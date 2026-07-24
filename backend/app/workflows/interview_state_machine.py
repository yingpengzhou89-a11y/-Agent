from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

from app.core.errors import AppError


class InterviewStatus(StrEnum):
    CREATED = "CREATED"
    PREPARING = "PREPARING"
    QUESTION_READY = "QUESTION_READY"
    WAITING_ANSWER = "WAITING_ANSWER"
    ANSWER_SAVED = "ANSWER_SAVED"
    EVALUATING = "EVALUATING"
    FOLLOW_UP_READY = "FOLLOW_UP_READY"
    NEXT_QUESTION_READY = "NEXT_QUESTION_READY"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    REPORT_GENERATING = "REPORT_GENERATING"
    REPORT_READY = "REPORT_READY"
    FAILED = "FAILED"


ALLOWED_TRANSITIONS: dict[InterviewStatus, set[InterviewStatus]] = {
    InterviewStatus.CREATED: {InterviewStatus.PREPARING, InterviewStatus.FAILED},
    InterviewStatus.PREPARING: {InterviewStatus.QUESTION_READY, InterviewStatus.FAILED},
    InterviewStatus.QUESTION_READY: {InterviewStatus.WAITING_ANSWER, InterviewStatus.COMPLETED, InterviewStatus.FAILED},
    InterviewStatus.WAITING_ANSWER: {InterviewStatus.ANSWER_SAVED, InterviewStatus.PAUSED, InterviewStatus.COMPLETED, InterviewStatus.FAILED},
    InterviewStatus.ANSWER_SAVED: {InterviewStatus.EVALUATING, InterviewStatus.FAILED},
    InterviewStatus.EVALUATING: {InterviewStatus.FOLLOW_UP_READY, InterviewStatus.NEXT_QUESTION_READY, InterviewStatus.COMPLETED, InterviewStatus.FAILED},
    InterviewStatus.FOLLOW_UP_READY: {InterviewStatus.WAITING_ANSWER, InterviewStatus.FAILED},
    InterviewStatus.NEXT_QUESTION_READY: {InterviewStatus.QUESTION_READY, InterviewStatus.FAILED},
    InterviewStatus.PAUSED: {InterviewStatus.WAITING_ANSWER, InterviewStatus.FOLLOW_UP_READY, InterviewStatus.QUESTION_READY, InterviewStatus.FAILED},
    InterviewStatus.COMPLETED: {InterviewStatus.REPORT_GENERATING},
    InterviewStatus.REPORT_GENERATING: {InterviewStatus.REPORT_READY, InterviewStatus.FAILED},
    InterviewStatus.REPORT_READY: set(),
    InterviewStatus.FAILED: set(),
}


@dataclass
class SessionState:
    status: InterviewStatus = InterviewStatus.CREATED
    follow_up_count: int = 0
    paused_from: InterviewStatus | None = None
    updated_at: datetime | None = None


class InterviewStateMachine:
    def transition(self, state: SessionState, target: InterviewStatus) -> SessionState:
        if target not in ALLOWED_TRANSITIONS[state.status]:
            raise AppError(
                "WORKFLOW_STATE_ERROR",
                f"不允许从 {state.status} 转换到 {target}",
                status_code=409,
            )
        state.status = target
        state.updated_at = datetime.now(timezone.utc)
        return state

    def pause(self, state: SessionState) -> SessionState:
        if state.status not in {InterviewStatus.WAITING_ANSWER, InterviewStatus.FOLLOW_UP_READY, InterviewStatus.QUESTION_READY}:
            raise AppError("WORKFLOW_STATE_ERROR", "当前状态不能暂停", status_code=409)
        state.paused_from = state.status
        return self.transition(state, InterviewStatus.PAUSED)

    def resume(self, state: SessionState) -> SessionState:
        if state.status != InterviewStatus.PAUSED or state.paused_from is None:
            raise AppError("WORKFLOW_STATE_ERROR", "当前会话不处于可恢复状态", status_code=409)
        target = state.paused_from
        state.paused_from = None
        return self.transition(state, target)

    def after_evaluation(self, state: SessionState, action: str, max_follow_ups: int) -> SessionState:
        if state.status != InterviewStatus.EVALUATING:
            raise AppError("WORKFLOW_STATE_ERROR", "只有评价完成后才能决定下一步", status_code=409)
        if action == "follow_up" and state.follow_up_count < max_follow_ups:
            state.follow_up_count += 1
            return self.transition(state, InterviewStatus.FOLLOW_UP_READY)
        if action in {"next", "follow_up"}:
            state.follow_up_count = 0
            return self.transition(state, InterviewStatus.NEXT_QUESTION_READY)
        if action == "finish":
            return self.transition(state, InterviewStatus.COMPLETED)
        raise AppError("WORKFLOW_STATE_ERROR", f"未知面试动作: {action}", status_code=422)

