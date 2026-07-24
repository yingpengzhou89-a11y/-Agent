from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.models.agent_audits import AgentDecisionLog
from app.models.base import Base
from app.models.documents import JobDescription, Resume
from app.models.interviews import InterviewPlan
from app.models.user import User
from app.schemas.interview import InterviewConfig, InterviewPlanDraft, InterviewSection, QuestionBlueprint
from app.schemas.interview import AnswerEvaluation, DimensionScores, InterviewDecision
from app.schemas.sessions import AnswerCreate
from app.services.interviews import EvaluationWorkflowService, InterviewSessionService
from app.workflows.interview_state_machine import InterviewStatus


@pytest.mark.asyncio
async def test_session_can_pause_resume_and_save_an_idempotent_answer(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'session.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        user = User(display_name="Tester")
        db.add(user)
        await db.flush()
        resume = Resume(user_id=user.id, name="r", file_type="text", raw_text="text")
        job = JobDescription(user_id=user.id, title="j", raw_text="text")
        db.add_all([resume, job])
        await db.flush()
        draft = InterviewPlanDraft(
            duration_minutes=30,
            difficulty="medium",
            sections=[InterviewSection(type="technical", weight=1, question_count=1)],
            question_blueprints=[
                QuestionBlueprint(
                    text="解释 RAG 的检索与生成流程。",
                    type="technical",
                    difficulty="medium",
                    skill_tags=["RAG"],
                    expected_points=["检索", "生成"],
                )
            ],
        )
        plan = InterviewPlan(
            user_id=user.id,
            resume_id=resume.id,
            job_id=job.id,
            config_json=InterviewConfig().model_dump(mode="json"),
            plan_json=draft.model_dump(mode="json"),
        )
        db.add(plan)
        await db.commit()

        service = InterviewSessionService()
        interview = await service.create(db, user.id, plan.id)
        await db.commit()
        await service.start(db, user.id, interview.id)
        await service.pause(db, user.id, interview.id)
        assert interview.status == InterviewStatus.PAUSED
        await service.resume(db, user.id, interview.id)
        assert interview.status == InterviewStatus.WAITING_ANSWER

        payload = AnswerCreate(answer_text="先检索相关文档，再将上下文交给模型生成。", idempotency_key="request-0001")
        first = await service.submit_answer(db, user.id, interview.id, payload)
        await db.commit()
        duplicate = await service.submit_answer(db, user.id, interview.id, payload)

        assert first.id == duplicate.id
        assert interview.status == InterviewStatus.ANSWER_SAVED

    await engine.dispose()


class FakeGateway:
    async def complete_structured(self, *, prompt_key, **kwargs):
        if prompt_key == "evaluation_agent/v1":
            return AnswerEvaluation(
                overall_score=1,
                dimension_scores=DimensionScores(
                    correctness=80,
                    completeness=70,
                    relevance=80,
                    depth=70,
                    clarity=80,
                    project_grounding=None,
                    credibility=80,
                ),
                improved_answer="先说明检索，再说明生成。",
                confidence=0.9,
            )
        return InterviewDecision(action="next", reason="基础回答已完成")


class FailingGateway:
    async def complete_structured(self, **kwargs):
        raise RuntimeError("provider unavailable")


@pytest.mark.parametrize(
    ("gateway", "expected_score", "execution_mode"),
    [(FakeGateway(), 76, "model"), (FailingGateway(), 34, "fallback")],
)
@pytest.mark.asyncio
async def test_evaluation_advances_to_the_next_planned_question_when_model_fails(
    tmp_path: Path, gateway, expected_score: int, execution_mode: str
) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'evaluation.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        user = User(display_name="Tester")
        db.add(user)
        await db.flush()
        resume = Resume(
            user_id=user.id,
            name="r",
            file_type="text",
            raw_text="FastAPI",
            parsed_profile_json={"education": [], "skills": ["FastAPI"], "projects": [], "experiences": [], "certificates": [], "target_roles": []},
        )
        job = JobDescription(
            user_id=user.id,
            title="j",
            raw_text="FastAPI",
            parsed_requirements_json={"job_title": "j", "responsibilities": [], "must_have_skills": ["FastAPI"], "nice_to_have_skills": [], "soft_skills": [], "seniority": "junior", "interview_focus": []},
        )
        db.add_all([resume, job])
        await db.flush()
        draft = InterviewPlanDraft(
            duration_minutes=30,
            difficulty="medium",
            sections=[InterviewSection(type="technical", weight=1, question_count=2)],
            question_blueprints=[
                QuestionBlueprint(text="问题一", type="technical", difficulty="medium", skill_tags=["FastAPI"], expected_points=["API"]),
                QuestionBlueprint(text="问题二", type="technical", difficulty="medium", skill_tags=["FastAPI"], expected_points=["依赖注入"]),
            ],
        )
        plan = InterviewPlan(
            user_id=user.id,
            resume_id=resume.id,
            job_id=job.id,
            config_json=InterviewConfig().model_dump(mode="json"),
            plan_json=draft.model_dump(mode="json"),
        )
        db.add(plan)
        await db.commit()

        sessions = InterviewSessionService()
        interview = await sessions.create(db, user.id, plan.id)
        await sessions.start(db, user.id, interview.id)
        await sessions.submit_answer(
            db, user.id, interview.id, AnswerCreate(answer_text="回答", idempotency_key="request-0002")
        )
        evaluation = await EvaluationWorkflowService(gateway).evaluate_current_answer(
            db, user.id, interview.id
        )

        assert evaluation.overall_score == expected_score
        assert evaluation.rubric_json["version"] == "v1"
        assert evaluation.generation_config_json["execution_mode"] == execution_mode
        assert evaluation.deterministic_checks_json == {
            "answer_non_empty": True,
            "minimum_length_met": False,
            "answer_char_count": 2,
            "expected_point_hits": [],
            "expected_point_coverage": 0.0,
            "project_evidence_available": False,
        }
        assert interview.status == InterviewStatus.WAITING_ANSWER
        assert interview.current_question_index == 1
        next_question = await sessions.sessions.get_question(db, interview.id, 1)
        assert next_question.question_text == "问题二"
        audit_logs = list((await db.scalars(select(AgentDecisionLog))).all())
        assert [(log.agent_name, log.action, log.execution_mode) for log in audit_logs] == [
            ("EvaluationAgent", "EVALUATE_ANSWER", execution_mode),
            ("InterviewAgent", "NEXT", execution_mode),
        ]

    await engine.dispose()
