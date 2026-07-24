import hashlib
import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.interview_agent import InterviewAgent
from app.agents.evaluation_agent import EvaluationAgent
from app.core.config import settings
from app.core.errors import AppError
from app.models.interviews import InterviewAnswer, InterviewPlan, InterviewQuestion, InterviewSession
from app.models.evaluations import AnswerEvaluation as AnswerEvaluationModel
from app.models.agent_audits import AgentDecisionLog
from app.repositories.agent_audits import AgentDecisionRepository
from app.repositories.documents import JobRepository, ResumeRepository
from app.repositories.evaluations import EvaluationRepository
from app.repositories.interviews import InterviewPlanRepository, InterviewSessionRepository
from app.schemas.interview import (
    AnswerEvaluation,
    AnswerSummary,
    DeterministicEvaluationChecks,
    EvaluationAgentInput,
    EvaluationRubric,
    InterviewAgentInput,
    InterviewConfig,
    InterviewPlanDraft,
    InterviewPlanningInput,
    InterviewQuestionDraft,
    SessionSnapshot,
)
from app.schemas.profiles import CandidateProfile, JobProfile
from app.schemas.sessions import AnswerCreate, InterviewPlanCreate
from app.services.model_gateway import StructuredModelGateway
from app.workflows.interview_state_machine import InterviewStatus


def question_fingerprint(text: str, skill_tags: list[str]) -> str:
    normalized_text = re.sub(r"\s+", " ", text).strip().casefold()
    raw = f"{normalized_text}|{'|'.join(sorted(skill_tags))}"
    return hashlib.sha256(raw.encode()).hexdigest()


class InterviewPlanService:
    def __init__(self, gateway: StructuredModelGateway) -> None:
        self.agent = InterviewAgent(gateway)
        self.resumes = ResumeRepository()
        self.jobs = JobRepository()
        self.plans = InterviewPlanRepository()
        self.audits = AgentDecisionRepository()

    async def create(
        self, session: AsyncSession, user_id: UUID, payload: InterviewPlanCreate
    ) -> InterviewPlan:
        resume = await self.resumes.get_for_user(session, user_id, payload.resume_id)
        job = await self.jobs.get_for_user(session, user_id, payload.job_id)
        if resume.parsed_profile_json is None or job.parsed_requirements_json is None:
            raise AppError("ANALYSIS_REQUIRED", "请先完成简历与 JD 的结构化分析", status_code=409)
        candidate = CandidateProfile.model_validate(resume.parsed_profile_json)
        job_profile = JobProfile.model_validate(job.parsed_requirements_json)
        planning_input = InterviewPlanningInput(
            candidate_profile=candidate,
            job_profile=job_profile,
            interview_config=payload.config,
        )
        try:
            draft = await self.agent.create_plan(
                AgentContext(
                    request_id=uuid4(),
                    user_id=user_id,
                    model_name=settings.chat_model or "unconfigured",
                    prompt_name="interview_plan",
                    prompt_version="v1",
                    token_budget=3500,
                ),
                planning_input,
            )
            execution_mode = "model"
        except Exception:
            draft = self._fallback_plan(planning_input)
            execution_mode = "fallback"
        plan = await self.plans.create(
            session,
            InterviewPlan(
                user_id=user_id,
                resume_id=payload.resume_id,
                job_id=payload.job_id,
                config_json=payload.config.model_dump(mode="json"),
                plan_json=draft.model_dump(mode="json"),
            ),
        )
        await self.audits.create(
            session,
            AgentDecisionLog(
                user_id=user_id,
                agent_name="InterviewAgent",
                action="CREATE_PLAN",
                execution_mode=execution_mode,
                input_summary_json={
                    "job_title": job_profile.job_title,
                    "candidate_skill_count": len(candidate.skills),
                    "must_have_skill_count": len(job_profile.must_have_skills),
                    "config": payload.config.model_dump(mode="json"),
                },
                output_json={
                    "question_count": len(draft.question_blueprints),
                    "section_count": len(draft.sections),
                    "difficulty": draft.difficulty,
                },
                model_name=settings.chat_model or "unconfigured",
                prompt_version="v1",
            ),
        )
        return plan

    @staticmethod
    def _fallback_plan(payload: InterviewPlanningInput) -> InterviewPlanDraft:
        """Keep the training workflow available when a provider cannot honor the JSON schema."""
        config = payload.interview_config
        job = payload.job_profile
        candidate = payload.candidate_profile
        skills = job.must_have_skills or candidate.skills or ["Python 基础"]
        primary_skill = skills[0]
        technical_questions = [
            InterviewQuestionDraft(
                text=f"请结合你的理解，说明 {primary_skill} 在 {job.job_title or '目标岗位'} 中的核心作用，以及实际落地时的关键注意点。",
                type="technical",
                difficulty=config.difficulty,
                skill_tags=[primary_skill],
                expected_points=["概念或职责解释", "具体实现方式", "常见风险与验证方法"],
            ),
            InterviewQuestionDraft(
                text="如果线上接口出现延迟升高或错误率上升，你会如何定位问题并制定修复方案？",
                type="system_design",
                difficulty=config.difficulty,
                skill_tags=[primary_skill, "问题排查"],
                expected_points=["先确认现象和影响范围", "结合日志、指标和链路定位", "提出修复、验证和回滚方案"],
            ),
        ]
        questions = technical_questions.copy()
        sections = [
            {"type": "technical", "weight": 0.5, "question_count": len(technical_questions)},
        ]
        if candidate.projects:
            project = candidate.projects[0]
            questions.append(
                InterviewQuestionDraft(
                    text=f"请介绍项目“{project.name}”中你负责的部分，并说明一个关键技术决策及其取舍。",
                    type="project",
                    difficulty=config.difficulty,
                    skill_tags=[primary_skill, "项目表达"],
                    expected_points=["个人职责边界", "技术决策依据", "结果与复盘"],
                    source_refs=project.evidence,
                )
            )
            sections.append({"type": "project", "weight": 0.25, "question_count": 1})
            behavioral_weight = 0.25
        else:
            behavioral_weight = 0.5
        questions.append(
            InterviewQuestionDraft(
                text="请举例说明你遇到一个不确定的技术问题时，如何拆解任务、沟通并推动问题解决。",
                type="behavioral",
                difficulty="easy",
                skill_tags=["沟通协作"],
                expected_points=["背景与目标", "具体行动", "结果与复盘"],
            )
        )
        sections.append({"type": "behavioral", "weight": behavioral_weight, "question_count": 1})
        return InterviewPlanDraft(
            duration_minutes=config.duration_minutes,
            difficulty=config.difficulty,
            sections=sections,
            question_blueprints=[question.model_dump(mode="json") for question in questions],
        )


class InterviewSessionService:
    def __init__(self) -> None:
        self.plans = InterviewPlanRepository()
        self.sessions = InterviewSessionRepository()

    async def create(self, session: AsyncSession, user_id: UUID, plan_id: UUID) -> InterviewSession:
        await self.plans.get_for_user(session, user_id, plan_id)
        return await self.sessions.create(session, InterviewSession(user_id=user_id, plan_id=plan_id))

    async def start(self, session: AsyncSession, user_id: UUID, session_id: UUID) -> InterviewSession:
        interview = await self.sessions.get_for_user(session, user_id, session_id)
        if interview.status != InterviewStatus.CREATED:
            raise AppError("WORKFLOW_STATE_ERROR", "只有新建会话可以开始", status_code=409)
        plan = await self.plans.get_for_user(session, user_id, interview.plan_id)
        draft = InterviewPlanDraft.model_validate(plan.plan_json)
        interview.status = InterviewStatus.PREPARING
        blueprint = draft.question_blueprints[0]
        await self.sessions.add_question(
            session,
            InterviewQuestion(
                session_id=interview.id,
                question_text=blueprint.text,
                question_type=blueprint.type,
                difficulty=blueprint.difficulty,
                skill_tags_json=blueprint.skill_tags,
                expected_points_json=blueprint.expected_points,
                source_refs_json=[ref.model_dump(mode="json") for ref in blueprint.source_refs],
                question_fingerprint=question_fingerprint(blueprint.text, blueprint.skill_tags),
                order_index=0,
            ),
        )
        interview.status = InterviewStatus.WAITING_ANSWER
        interview.started_at = datetime.now(timezone.utc)
        await session.flush()
        return interview

    async def pause(self, session: AsyncSession, user_id: UUID, session_id: UUID) -> InterviewSession:
        interview = await self.sessions.get_for_user(session, user_id, session_id)
        if interview.status != InterviewStatus.WAITING_ANSWER:
            raise AppError("WORKFLOW_STATE_ERROR", "当前状态不能暂停", status_code=409)
        interview.last_valid_state = interview.status
        interview.status = InterviewStatus.PAUSED
        interview.paused_at = datetime.now(timezone.utc)
        await session.flush()
        return interview

    async def resume(self, session: AsyncSession, user_id: UUID, session_id: UUID) -> InterviewSession:
        interview = await self.sessions.get_for_user(session, user_id, session_id)
        if interview.status != InterviewStatus.PAUSED or interview.last_valid_state is None:
            raise AppError("WORKFLOW_STATE_ERROR", "当前会话不处于可恢复状态", status_code=409)
        interview.status = interview.last_valid_state
        interview.last_valid_state = None
        interview.paused_at = None
        await session.flush()
        return interview

    async def submit_answer(
        self, session: AsyncSession, user_id: UUID, session_id: UUID, payload: AnswerCreate
    ) -> InterviewAnswer:
        interview = await self.sessions.get_for_user(session, user_id, session_id)
        if interview.status not in {InterviewStatus.WAITING_ANSWER, InterviewStatus.ANSWER_SAVED}:
            raise AppError("WORKFLOW_STATE_ERROR", "当前状态不能提交回答", status_code=409)
        question = await self.sessions.get_question(
            session, interview.id, interview.current_question_index
        )
        if question is None:
            raise AppError("WORKFLOW_STATE_ERROR", "当前题目不存在", status_code=409)
        previous = await self.sessions.get_answer_by_key(session, question.id, payload.idempotency_key)
        if previous is not None:
            return previous
        if interview.status == InterviewStatus.ANSWER_SAVED:
            raise AppError("WORKFLOW_STATE_ERROR", "当前题目已经提交过回答", status_code=409)
        answer = await self.sessions.add_answer(
            session,
            InterviewAnswer(
                question_id=question.id,
                user_id=user_id,
                answer_text=payload.answer_text,
                duration_seconds=payload.duration_seconds,
                hint_used=payload.hint_used,
                idempotency_key=payload.idempotency_key,
            ),
        )
        interview.status = InterviewStatus.ANSWER_SAVED
        await session.flush()
        return answer


class EvaluationWorkflowService:
    def __init__(self, gateway: StructuredModelGateway) -> None:
        self.evaluator = EvaluationAgent(gateway)
        self.interviewer = InterviewAgent(gateway)
        self.sessions = InterviewSessionRepository()
        self.plans = InterviewPlanRepository()
        self.resumes = ResumeRepository()
        self.jobs = JobRepository()
        self.evaluations = EvaluationRepository()
        self.audits = AgentDecisionRepository()

    async def evaluate_current_answer(
        self, session: AsyncSession, user_id: UUID, session_id: UUID
    ) -> AnswerEvaluationModel:
        interview = await self.sessions.get_for_user(session, user_id, session_id)
        if interview.status != InterviewStatus.ANSWER_SAVED:
            raise AppError("WORKFLOW_STATE_ERROR", "当前没有待评价的回答", status_code=409)
        question = await self.sessions.get_question(session, interview.id, interview.current_question_index)
        if question is None:
            raise AppError("WORKFLOW_STATE_ERROR", "当前题目不存在", status_code=409)
        answer = await self.sessions.get_answer_for_question(session, question.id)
        if answer is None:
            raise AppError("WORKFLOW_STATE_ERROR", "当前回答不存在", status_code=409)
        plan = await self.plans.get_for_user(session, user_id, interview.plan_id)
        resume = await self.resumes.get_for_user(session, user_id, plan.resume_id)
        job = await self.jobs.get_for_user(session, user_id, plan.job_id)
        if resume.parsed_profile_json is None or job.parsed_requirements_json is None:
            raise AppError("ANALYSIS_REQUIRED", "简历或 JD 分析结果不存在", status_code=409)
        candidate = CandidateProfile.model_validate(resume.parsed_profile_json)
        job_profile = JobProfile.model_validate(job.parsed_requirements_json)
        rubric = EvaluationRubric()
        interview.status = InterviewStatus.EVALUATING
        evaluation_input = EvaluationAgentInput(
            question=InterviewQuestionDraft(
                text=question.question_text,
                type=question.question_type,
                difficulty=question.difficulty,
                skill_tags=question.skill_tags_json,
                expected_points=question.expected_points_json,
                source_refs=question.source_refs_json,
            ),
            user_answer=answer.answer_text,
            candidate_profile=candidate,
            retrieved_context=[],
            evaluation_rubric=rubric,
            interview_level=job_profile.seniority if job_profile.seniority != "unknown" else "junior",
        )
        deterministic_checks = self._deterministic_checks(evaluation_input)
        try:
            result = await self.evaluator.run(
                AgentContext(
                    request_id=uuid4(),
                    user_id=user_id,
                    session_id=interview.id,
                    model_name=settings.chat_model or "unconfigured",
                    prompt_name="evaluation_agent",
                    prompt_version="v1",
                    token_budget=3000,
                ),
                evaluation_input,
            )
            execution_mode = "model"
        except Exception:
            result = self._fallback_evaluation(evaluation_input)
            execution_mode = "fallback"
        result = result.model_copy(
            update={
                "overall_score": result.recompute_score(rubric),
                "deterministic_checks": deterministic_checks,
            }
        )
        saved = await self.evaluations.create(
            session, self._to_model(answer.id, result, rubric, execution_mode)
        )
        await self.audits.create(
            session,
            AgentDecisionLog(
                user_id=user_id,
                session_id=interview.id,
                agent_name="EvaluationAgent",
                action="EVALUATE_ANSWER",
                execution_mode=execution_mode,
                input_summary_json={
                    "question_type": question.question_type,
                    "skill_tags": question.skill_tags_json,
                    "answer_char_count": deterministic_checks.answer_char_count,
                    "rubric_version": rubric.version,
                },
                output_json={
                    "overall_score": result.overall_score,
                    "dimension_scores": result.dimension_scores.model_dump(),
                    "confidence": result.confidence,
                    "expected_point_coverage": deterministic_checks.expected_point_coverage,
                },
                model_name=settings.chat_model or "unconfigured",
                prompt_version="v1",
            ),
        )
        await self._advance_after_evaluation(
            session, user_id, interview, plan, candidate, job_profile, question, answer.id, result
        )
        await session.flush()
        return saved

    @staticmethod
    def _to_model(
        answer_id: UUID,
        evaluation: AnswerEvaluation,
        rubric: EvaluationRubric,
        execution_mode: str,
    ) -> AnswerEvaluationModel:
        return AnswerEvaluationModel(
            answer_id=answer_id,
            overall_score=evaluation.overall_score,
            dimension_scores_json=evaluation.dimension_scores.model_dump(),
            strengths_json=evaluation.strengths,
            errors_json=[item.model_dump() for item in evaluation.errors],
            missing_points_json=evaluation.missing_points,
            advice_json=evaluation.improvement_advice,
            answer_framework_json=evaluation.answer_framework,
            improved_answer=evaluation.improved_answer,
            practice_questions_json=evaluation.practice_questions,
            confidence=evaluation.confidence,
            model_name=settings.chat_model or "unconfigured",
            prompt_version="v1",
            rubric_json=rubric.model_dump(),
            generation_config_json={
                "execution_mode": execution_mode,
                "temperature": 0,
                "token_budget": 3000,
            },
            deterministic_checks_json=(
                evaluation.deterministic_checks.model_dump() if evaluation.deterministic_checks else None
            ),
        )

    @staticmethod
    def _deterministic_checks(payload: EvaluationAgentInput) -> DeterministicEvaluationChecks:
        answer = payload.user_answer.strip()
        answer_folded = answer.casefold()
        expected_point_hits = [
            point for point in payload.question.expected_points if point.casefold() in answer_folded
        ]
        expected_count = len(payload.question.expected_points)
        return DeterministicEvaluationChecks(
            answer_non_empty=bool(answer),
            minimum_length_met=len(answer) >= 40,
            answer_char_count=len(answer),
            expected_point_hits=expected_point_hits,
            expected_point_coverage=round(len(expected_point_hits) / expected_count, 3)
            if expected_count
            else 1,
            project_evidence_available=bool(payload.question.source_refs),
        )

    @staticmethod
    def _fallback_evaluation(payload: EvaluationAgentInput) -> AnswerEvaluation:
        answer = payload.user_answer.strip()
        covered = [point for point in payload.question.expected_points if point.casefold() in answer.casefold()]
        score = min(78, max(35, 35 + len(answer) // 25 + len(covered) * 12))
        return AnswerEvaluation(
            overall_score=score,
            dimension_scores={
                "correctness": score, "completeness": max(30, score - 8),
                "relevance": min(85, score + 5), "depth": max(25, score - 12),
                "clarity": min(85, score + 3), "project_grounding": None,
                "credibility": min(90, score + 8),
            },
            strengths=["已完成本题回答并形成可复盘记录"],
            missing_points=[point for point in payload.question.expected_points if point not in covered],
            improvement_advice=["使用“背景—方案—取舍—结果”结构回答", "补充具体实现细节与验证方式"],
            answer_framework=["明确问题目标", "说明核心方案与关键步骤", "补充风险、取舍和结果"],
            improved_answer="模型评价暂不可用。请补充具体方案、关键实现、验证方式和复盘结果。",
            practice_questions=[payload.question.text],
            confidence=0.35,
        )

    async def _advance_after_evaluation(
        self,
        session: AsyncSession,
        user_id: UUID,
        interview: InterviewSession,
        plan: InterviewPlan,
        candidate: CandidateProfile,
        job: JobProfile,
        question: InterviewQuestion,
        answer_id: UUID,
        evaluation: AnswerEvaluation,
    ) -> None:
        config = InterviewConfig.model_validate(plan.config_json)
        fingerprints = await self.sessions.list_fingerprints(session, interview.id)
        try:
            decision = await self.interviewer.run(
                AgentContext(
                    request_id=uuid4(),
                    user_id=user_id,
                    session_id=interview.id,
                    model_name=settings.chat_model or "unconfigured",
                    prompt_name="interview_agent",
                    prompt_version="v1",
                    token_budget=1500,
                ),
                InterviewAgentInput(
                    candidate_profile=candidate,
                    job_profile=job,
                    interview_config=config,
                    session_state=SessionSnapshot(
                        asked_question_ids=[],
                        current_question_id=question.id,
                        follow_up_count=interview.follow_up_count,
                        remaining_minutes=config.duration_minutes,
                    ),
                    latest_answer_summary=AnswerSummary(
                        answer_id=answer_id,
                        answered=evaluation.overall_score > 0,
                        strengths=evaluation.strengths,
                        gaps=[*evaluation.missing_points, *(issue.issue for issue in evaluation.errors)],
                        confidence=evaluation.confidence,
                    ),
                    retrieved_context=[],
                ),
            )
            execution_mode = "model"
        except Exception:
            decision = None
            execution_mode = "fallback"
        if decision is None:
            next_question = self._next_blueprint(plan, fingerprints)
            action = "FINISH" if next_question is None else "NEXT"
            await self._log_interview_decision(
                session, user_id, interview, question, config, execution_mode, action,
                "模型决策不可用，按既定题目蓝图推进",
            )
            if next_question is None:
                interview.status = InterviewStatus.COMPLETED
                interview.completed_at = datetime.now(timezone.utc)
            else:
                await self._add_question(session, interview, next_question)
                interview.follow_up_count = 0
                interview.status = InterviewStatus.WAITING_ANSWER
            return
        await self._log_interview_decision(
            session,
            user_id,
            interview,
            question,
            config,
            execution_mode,
            decision.action.upper(),
            decision.reason,
        )
        if decision.action == "follow_up" and interview.follow_up_count < config.max_follow_ups:
            await self._add_question(session, interview, decision.question, parent_id=question.id)
            interview.follow_up_count += 1
            interview.status = InterviewStatus.WAITING_ANSWER
            return
        if decision.action in {"next", "follow_up"}:
            next_question = self._next_blueprint(plan, fingerprints)
            if next_question is None:
                interview.status = InterviewStatus.COMPLETED
                interview.completed_at = datetime.now(timezone.utc)
                return
            await self._add_question(session, interview, next_question)
            interview.follow_up_count = 0
            interview.status = InterviewStatus.WAITING_ANSWER
            return
        if decision.action == "finish":
            interview.status = InterviewStatus.COMPLETED
            interview.completed_at = datetime.now(timezone.utc)
            return
        raise AppError("WORKFLOW_STATE_ERROR", "Interview Agent 返回了无效的后续动作", status_code=502)

    async def _log_interview_decision(
        self,
        session: AsyncSession,
        user_id: UUID,
        interview: InterviewSession,
        question: InterviewQuestion,
        config: InterviewConfig,
        execution_mode: str,
        action: str,
        reason: str,
    ) -> None:
        await self.audits.create(
            session,
            AgentDecisionLog(
                user_id=user_id,
                session_id=interview.id,
                agent_name="InterviewAgent",
                action=action,
                execution_mode=execution_mode,
                input_summary_json={
                    "current_question_type": question.question_type,
                    "skill_tags": question.skill_tags_json,
                    "follow_up_count": interview.follow_up_count,
                    "max_follow_ups": config.max_follow_ups,
                },
                output_json={"reason": reason, "current_question_index": interview.current_question_index},
                model_name=settings.chat_model or "unconfigured",
                prompt_version="v1",
            ),
        )

    async def _add_question(
        self, session: AsyncSession, interview: InterviewSession, question, parent_id: UUID | None = None
    ) -> None:
        if question is None:
            raise AppError("MODEL_OUTPUT_INVALID", "追问缺少题目内容", retryable=True, status_code=502)
        interview.current_question_index += 1
        await self.sessions.add_question(
            session,
            InterviewQuestion(
                session_id=interview.id,
                parent_question_id=parent_id,
                question_text=question.text,
                question_type=question.type,
                difficulty=question.difficulty,
                skill_tags_json=question.skill_tags,
                expected_points_json=question.expected_points,
                source_refs_json=[ref.model_dump(mode="json") for ref in question.source_refs],
                question_fingerprint=question_fingerprint(question.text, question.skill_tags),
                order_index=interview.current_question_index,
            ),
        )

    @staticmethod
    def _next_blueprint(plan: InterviewPlan, existing_fingerprints: list[str]):
        for blueprint in InterviewPlanDraft.model_validate(plan.plan_json).question_blueprints:
            if question_fingerprint(blueprint.text, blueprint.skill_tags) not in existing_fingerprints:
                return blueprint
        return None
