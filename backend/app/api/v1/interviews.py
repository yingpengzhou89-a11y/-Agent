from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_id
from app.db.session import get_db_session
from app.repositories.interviews import InterviewPlanRepository, InterviewSessionRepository
from app.repositories.evaluations import EvaluationRepository
from app.repositories.progress import ReportRepository
from app.schemas.interview import InterviewConfig, InterviewPlanDraft
from app.schemas.sessions import (
    AnswerCreate,
    AnswerRead,
    EvaluationRead,
    InterviewPlanCreate,
    InterviewPlanRead,
    InterviewQuestionRead,
    InterviewSessionCreate,
    InterviewSessionRead,
)
from app.schemas.progress import InterviewReportRead
from app.services.interviews import EvaluationWorkflowService, InterviewPlanService, InterviewSessionService
from app.services.model_gateway import OpenAICompatibleGateway
from app.services.progress import ReportService

router = APIRouter(tags=["interviews"])
plan_service = InterviewPlanService(OpenAICompatibleGateway())
session_service = InterviewSessionService()
evaluation_service = EvaluationWorkflowService(OpenAICompatibleGateway())
plans = InterviewPlanRepository()
sessions = InterviewSessionRepository()
evaluations = EvaluationRepository()
reports = ReportRepository()
report_service = ReportService()


def plan_read(plan) -> InterviewPlanRead:
    return InterviewPlanRead(
        id=plan.id,
        user_id=plan.user_id,
        resume_id=plan.resume_id,
        job_id=plan.job_id,
        config=InterviewConfig.model_validate(plan.config_json),
        plan=InterviewPlanDraft.model_validate(plan.plan_json),
        status=plan.status,
        created_at=plan.created_at,
    )


def session_read(interview) -> InterviewSessionRead:
    return InterviewSessionRead(
        id=interview.id,
        plan_id=interview.plan_id,
        status=interview.status,
        current_question_index=interview.current_question_index,
        follow_up_count=interview.follow_up_count,
        started_at=interview.started_at,
        paused_at=interview.paused_at,
        completed_at=interview.completed_at,
    )


def evaluation_read(evaluation) -> EvaluationRead:
    return EvaluationRead(
        answer_id=evaluation.answer_id,
        overall_score=evaluation.overall_score,
        dimension_scores=evaluation.dimension_scores_json,
        strengths=evaluation.strengths_json,
        errors=evaluation.errors_json,
        missing_points=evaluation.missing_points_json,
        improvement_advice=evaluation.advice_json,
        answer_framework=evaluation.answer_framework_json,
        improved_answer=evaluation.improved_answer,
        practice_questions=evaluation.practice_questions_json,
        confidence=evaluation.confidence,
        deterministic_checks=evaluation.deterministic_checks_json,
        rubric=evaluation.rubric_json,
        generation_config=evaluation.generation_config_json,
        created_at=evaluation.created_at,
    )


def report_read(report) -> InterviewReportRead:
    return InterviewReportRead(
        id=report.id,
        session_id=report.session_id,
        summary=report.summary_json,
        weak_topics=report.weak_topics_json,
        recommended_actions=report.recommended_actions_json,
        created_at=report.created_at,
    )


@router.post("/api/v1/interview-plans", response_model=InterviewPlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(
    payload: InterviewPlanCreate,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> InterviewPlanRead:
    plan = await plan_service.create(session, user_id, payload)
    await session.commit()
    return plan_read(plan)


@router.get("/api/v1/interview-plans/{plan_id}", response_model=InterviewPlanRead)
async def get_plan(
    plan_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> InterviewPlanRead:
    return plan_read(await plans.get_for_user(session, user_id, plan_id))


@router.post("/api/v1/interviews", response_model=InterviewSessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: InterviewSessionCreate,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> InterviewSessionRead:
    interview = await session_service.create(session, user_id, payload.plan_id)
    await session.commit()
    return session_read(interview)


@router.get("/api/v1/interviews/{session_id}", response_model=InterviewSessionRead)
async def get_session(
    session_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> InterviewSessionRead:
    return session_read(await sessions.get_for_user(session, user_id, session_id))


@router.post("/api/v1/interviews/{session_id}/start", response_model=InterviewSessionRead)
async def start_session(
    session_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> InterviewSessionRead:
    interview = await session_service.start(session, user_id, session_id)
    await session.commit()
    return session_read(interview)


@router.post("/api/v1/interviews/{session_id}/pause", response_model=InterviewSessionRead)
async def pause_session(
    session_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> InterviewSessionRead:
    interview = await session_service.pause(session, user_id, session_id)
    await session.commit()
    return session_read(interview)


@router.post("/api/v1/interviews/{session_id}/resume", response_model=InterviewSessionRead)
async def resume_session(
    session_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> InterviewSessionRead:
    interview = await session_service.resume(session, user_id, session_id)
    await session.commit()
    return session_read(interview)


@router.get("/api/v1/interviews/{session_id}/question", response_model=InterviewQuestionRead)
async def current_question(
    session_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> InterviewQuestionRead:
    interview = await sessions.get_for_user(session, user_id, session_id)
    question = await sessions.get_question(session, interview.id, interview.current_question_index)
    if question is None:
        from app.core.errors import AppError

        raise AppError("NOT_FOUND", "当前没有可展示的题目", status_code=404)
    return InterviewQuestionRead(
        id=question.id,
        question_text=question.question_text,
        question_type=question.question_type,
        difficulty=question.difficulty,
        skill_tags=question.skill_tags_json,
        order_index=question.order_index,
    )


@router.post("/api/v1/interviews/{session_id}/answers", response_model=AnswerRead, status_code=status.HTTP_201_CREATED)
async def submit_answer(
    session_id: UUID,
    payload: AnswerCreate,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> AnswerRead:
    answer = await session_service.submit_answer(session, user_id, session_id, payload)
    await session.commit()
    return AnswerRead.model_validate(answer)


@router.post("/api/v1/interviews/{session_id}/evaluate", response_model=EvaluationRead)
async def evaluate_answer(
    session_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> EvaluationRead:
    evaluation = await evaluation_service.evaluate_current_answer(session, user_id, session_id)
    await session.commit()
    return evaluation_read(evaluation)


@router.get("/api/v1/answers/{answer_id}/evaluation", response_model=EvaluationRead)
async def get_evaluation(
    answer_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> EvaluationRead:
    await sessions.get_answer_for_user(session, user_id, answer_id)
    return evaluation_read(await evaluations.get(session, answer_id))


@router.post("/api/v1/interviews/{session_id}/report/regenerate", response_model=InterviewReportRead)
async def generate_report(
    session_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> InterviewReportRead:
    report = await report_service.generate(session, user_id, session_id)
    await session.commit()
    return report_read(report)


@router.get("/api/v1/interviews/{session_id}/report", response_model=InterviewReportRead)
async def get_report(
    session_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> InterviewReportRead:
    await sessions.get_for_user(session, user_id, session_id)
    report = await reports.get_for_session(session, session_id)
    if report is None:
        from app.core.errors import AppError

        raise AppError("NOT_FOUND", "尚未生成面试报告", status_code=404)
    return report_read(report)
