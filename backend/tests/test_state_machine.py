import pytest

from app.core.errors import AppError
from app.workflows.interview_state_machine import InterviewStateMachine, InterviewStatus, SessionState


def to_evaluating(machine: InterviewStateMachine, state: SessionState) -> SessionState:
    for target in (
        InterviewStatus.PREPARING,
        InterviewStatus.QUESTION_READY,
        InterviewStatus.WAITING_ANSWER,
        InterviewStatus.ANSWER_SAVED,
        InterviewStatus.EVALUATING,
    ):
        machine.transition(state, target)
    return state


def test_follow_up_is_limited_then_advances() -> None:
    machine = InterviewStateMachine()
    state = to_evaluating(machine, SessionState(follow_up_count=1))

    machine.after_evaluation(state, "follow_up", max_follow_ups=2)
    assert state.status == InterviewStatus.FOLLOW_UP_READY
    assert state.follow_up_count == 2

    machine.transition(state, InterviewStatus.WAITING_ANSWER)
    machine.transition(state, InterviewStatus.ANSWER_SAVED)
    machine.transition(state, InterviewStatus.EVALUATING)
    machine.after_evaluation(state, "follow_up", max_follow_ups=2)

    assert state.status == InterviewStatus.NEXT_QUESTION_READY
    assert state.follow_up_count == 0


def test_pause_resume_restores_previous_state() -> None:
    machine = InterviewStateMachine()
    state = SessionState(status=InterviewStatus.WAITING_ANSWER)

    machine.pause(state)
    assert state.status == InterviewStatus.PAUSED
    machine.resume(state)

    assert state.status == InterviewStatus.WAITING_ANSWER
    assert state.paused_from is None


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(AppError):
        InterviewStateMachine().transition(SessionState(), InterviewStatus.EVALUATING)

