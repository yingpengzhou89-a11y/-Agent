from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.interviews import InterviewSession
from app.models.progress import InterviewReport, SkillMastery
from app.repositories.interviews import InterviewSessionRepository
from app.repositories.progress import ProgressRepository, ReportRepository
from app.schemas.progress import ProgressOverview, SkillMasteryRead
from app.workflows.interview_state_machine import InterviewStatus


class ProgressService:
    def __init__(self) -> None:
        self.progress = ProgressRepository()

    async def apply_skill_scores(
        self, session: AsyncSession, user_id: UUID, skill_scores: dict[str, list[int]]
    ) -> None:
        now = datetime.now(timezone.utc)
        for skill, scores in skill_scores.items():
            if not scores:
                continue
            latest_score = round(sum(scores) / len(scores), 1)
            record = await self.progress.get(session, user_id, skill)
            if record is None:
                mastery = latest_score
                correct_streak, incorrect_streak = self._updated_streaks(latest_score, 0, 0)
                record = SkillMastery(
                    user_id=user_id,
                    skill_name=skill,
                    mastery_score=mastery,
                    attempt_count=len(scores),
                    consecutive_correct_count=correct_streak,
                    consecutive_incorrect_count=incorrect_streak,
                    last_score=latest_score,
                    last_practiced_at=now,
                    next_review_at=self._next_review(now, mastery, correct_streak, incorrect_streak),
                    evidence_json={
                        "latest_score": latest_score,
                        "attempts_added": len(scores),
                        "schedule_rule_version": "review_schedule/v2",
                    },
                    updated_at=now,
                )
            else:
                elapsed_days = max((now - record.updated_at).days, 0)
                decayed = record.mastery_score * max(0.7, 1 - elapsed_days * 0.01)
                mastery = round(decayed * 0.7 + latest_score * 0.3, 1)
                correct_streak, incorrect_streak = self._updated_streaks(
                    latest_score, record.consecutive_correct_count, record.consecutive_incorrect_count
                )
                record.mastery_score = mastery
                record.attempt_count += len(scores)
                record.consecutive_correct_count = correct_streak
                record.consecutive_incorrect_count = incorrect_streak
                record.last_score = latest_score
                record.last_practiced_at = now
                record.next_review_at = self._next_review(
                    now, mastery, correct_streak, incorrect_streak
                )
                record.evidence_json = {
                    "latest_score": latest_score,
                    "attempts_added": len(scores),
                    "schedule_rule_version": "review_schedule/v2",
                }
                record.updated_at = now
            await self.progress.save(session, record)

    @staticmethod
    def _updated_streaks(score: float, correct_streak: int, incorrect_streak: int) -> tuple[int, int]:
        if score >= 80:
            return correct_streak + 1, 0
        if score < 60:
            return 0, incorrect_streak + 1
        return 0, 0

    @staticmethod
    def _next_review(
        now: datetime, mastery: float, correct_streak: int = 0, incorrect_streak: int = 0
    ) -> datetime:
        if mastery < 60 or incorrect_streak >= 2:
            days = 1
        elif mastery < 80:
            days = 3
        else:
            days = 7
        if mastery >= 80 and correct_streak >= 2:
            days = min(21, days + 7 * (correct_streak - 1))
        return now + timedelta(days=days)

    async def overview(self, session: AsyncSession, user_id: UUID) -> ProgressOverview:
        completed = await session.scalar(
            select(func.count()).select_from(InterviewSession).where(
                InterviewSession.user_id == user_id,
                InterviewSession.status == InterviewStatus.COMPLETED,
            )
        )
        from app.models.evaluations import AnswerEvaluation
        from app.models.interviews import InterviewAnswer

        evaluated = await session.scalar(
            select(func.count())
            .select_from(AnswerEvaluation)
            .join(InterviewAnswer, InterviewAnswer.id == AnswerEvaluation.answer_id)
            .where(InterviewAnswer.user_id == user_id)
        )
        skills = await self.progress.list_for_user(session, user_id)
        return ProgressOverview(
            completed_interviews=completed or 0,
            evaluated_answers=evaluated or 0,
            weakest_topics=[item.skill_name for item in skills[:5]],
            next_reviews=[SkillMasteryRead.model_validate(item) for item in skills[:5]],
        )


class ReportService:
    def __init__(self) -> None:
        self.sessions = InterviewSessionRepository()
        self.reports = ReportRepository()
        self.progress = ProgressService()

    async def generate(self, session: AsyncSession, user_id: UUID, session_id: UUID) -> InterviewReport:
        interview = await self.sessions.get_for_user(session, user_id, session_id)
        if interview.status != InterviewStatus.COMPLETED:
            raise AppError("WORKFLOW_STATE_ERROR", "面试完成后才能生成整场报告", status_code=409)
        items = await self.reports.evaluated_items(session, session_id)
        if not items:
            raise AppError("REPORT_DATA_INCOMPLETE", "没有已评价的回答，无法生成报告", status_code=409)
        existing = await self.reports.get_for_session(session, session_id)
        summary, weak_topics, actions, skill_scores = self._summarize(items)
        if existing is None:
            report = InterviewReport(
                session_id=session_id,
                summary_json=summary,
                weak_topics_json=weak_topics,
                recommended_actions_json=actions,
            )
            await self.progress.apply_skill_scores(session, user_id, skill_scores)
            return await self.reports.save(session, report)
        existing.summary_json = summary
        existing.weak_topics_json = weak_topics
        existing.recommended_actions_json = actions
        return await self.reports.save(session, existing)

    @staticmethod
    def _summarize(items):
        overall_scores: list[int] = []
        confidences: list[float] = []
        dimension_scores: dict[str, list[int]] = defaultdict(list)
        skill_scores: dict[str, list[int]] = defaultdict(list)
        for question, _, evaluation in items:
            overall_scores.append(evaluation.overall_score)
            confidences.append(getattr(evaluation, "confidence", 1.0))
            for dimension, score in evaluation.dimension_scores_json.items():
                if score is not None:
                    dimension_scores[dimension].append(score)
            for skill in question.skill_tags_json:
                skill_scores[skill].append(evaluation.overall_score)
        per_skill = {skill: round(sum(scores) / len(scores), 1) for skill, scores in skill_scores.items()}
        sorted_skills = sorted(per_skill, key=per_skill.get)
        weak_topics = sorted_skills[:5]
        strong_skills = list(reversed(sorted_skills[-5:]))
        actions = [
            *[f"优先复习：{topic}" for topic in weak_topics[:3]],
            "完成复习后重新进行一场针对性模拟面试。",
        ]
        low_confidence_count = sum(confidence < 0.6 for confidence in confidences)
        if low_confidence_count:
            actions.append("本场存在低置信度评价，请结合原回答与资料进行人工复核。")
        summary = {
            "overall_score": round(sum(overall_scores) / len(overall_scores), 1),
            "dimension_scores": {
                name: round(sum(scores) / len(scores), 1) for name, scores in dimension_scores.items()
            },
            "evaluated_question_count": len(items),
            "strong_skills": strong_skills,
            "weak_topics": weak_topics,
            "average_confidence": round(sum(confidences) / len(confidences), 2),
            "low_confidence_answer_count": low_confidence_count,
            "manual_review_recommended": low_confidence_count > 0,
        }
        return summary, weak_topics, actions, skill_scores
