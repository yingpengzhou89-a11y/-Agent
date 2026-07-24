from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.profiles import CandidateProfile, JobProfile, SourceRef

QuestionType = Literal["technical", "project", "behavioral", "coding", "system_design"]
Difficulty = Literal["easy", "medium", "hard"]


class InterviewConfig(BaseModel):
    duration_minutes: int = Field(default=45, ge=15, le=180)
    difficulty: Difficulty = "medium"
    style: Literal["friendly", "standard", "project_deep_dive", "pressure"] = "standard"
    max_follow_ups: int = Field(default=1, ge=0, le=5)
    technical_weight: float = Field(default=0.5, ge=0, le=1)
    project_weight: float = Field(default=0.3, ge=0, le=1)
    behavioral_weight: float = Field(default=0.2, ge=0, le=1)

    @model_validator(mode="after")
    def weights_total_one(self) -> "InterviewConfig":
        if abs(self.technical_weight + self.project_weight + self.behavioral_weight - 1) > 0.001:
            raise ValueError("题型权重之和必须为 1")
        return self


class SessionSnapshot(BaseModel):
    asked_question_ids: list[UUID] = []
    current_question_id: UUID | None = None
    follow_up_count: int = Field(default=0, ge=0)
    remaining_minutes: int = Field(ge=0)


class AnswerSummary(BaseModel):
    answer_id: UUID
    answered: bool
    strengths: list[str] = []
    gaps: list[str] = []
    confidence: float = Field(ge=0, le=1)


class InterviewQuestionDraft(BaseModel):
    text: str = Field(min_length=3, max_length=2000)
    type: QuestionType
    difficulty: Difficulty
    skill_tags: list[str] = Field(min_length=1, max_length=8)
    expected_points: list[str] = Field(min_length=1, max_length=12)
    source_refs: list[SourceRef] = []

    @model_validator(mode="after")
    def project_question_requires_sources(self) -> "InterviewQuestionDraft":
        if self.type == "project" and not self.source_refs:
            raise ValueError("项目问题必须包含来源")
        return self


class InterviewDecision(BaseModel):
    action: Literal["ask", "follow_up", "next", "finish"]
    question: InterviewQuestionDraft | None = None
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def question_matches_action(self) -> "InterviewDecision":
        needs_question = self.action in {"ask", "follow_up"}
        if needs_question != (self.question is not None):
            raise ValueError("ask/follow_up 必须且只能包含一个问题")
        return self


class InterviewAgentInput(BaseModel):
    candidate_profile: CandidateProfile
    job_profile: JobProfile
    interview_config: InterviewConfig
    session_state: SessionSnapshot
    latest_answer_summary: AnswerSummary | None = None
    retrieved_context: list[SourceRef] = []


class InterviewSection(BaseModel):
    type: QuestionType
    weight: float = Field(ge=0, le=1)
    question_count: int = Field(ge=1, le=20)


class QuestionBlueprint(InterviewQuestionDraft):
    pass


class InterviewPlanDraft(BaseModel):
    duration_minutes: int = Field(ge=15, le=180)
    difficulty: Difficulty
    sections: list[InterviewSection] = Field(min_length=1, max_length=6)
    question_blueprints: list[QuestionBlueprint] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def validate_plan(self) -> "InterviewPlanDraft":
        if abs(sum(section.weight for section in self.sections) - 1) > 0.001:
            raise ValueError("面试章节权重之和必须为 1")
        if sum(section.question_count for section in self.sections) != len(self.question_blueprints):
            raise ValueError("章节题数之和必须等于题目蓝图数量")
        return self


class InterviewPlanningInput(BaseModel):
    candidate_profile: CandidateProfile
    job_profile: JobProfile
    interview_config: InterviewConfig
    weak_topics: list[str] = []
    asked_fingerprints: list[str] = []


class DimensionScores(BaseModel):
    correctness: int = Field(ge=0, le=100)
    completeness: int = Field(ge=0, le=100)
    relevance: int = Field(ge=0, le=100)
    depth: int = Field(ge=0, le=100)
    clarity: int = Field(ge=0, le=100)
    project_grounding: int | None = Field(default=None, ge=0, le=100)
    credibility: int = Field(ge=0, le=100)


class EvaluationIssue(BaseModel):
    issue: str = Field(min_length=1, max_length=1000)
    impact: Literal["minor", "major", "critical"]
    deduction_reason: str = Field(min_length=1, max_length=1000)


class EvaluationRubric(BaseModel):
    version: str = "v1"
    correctness: float = Field(default=0.25, ge=0, le=1)
    completeness: float = Field(default=0.20, ge=0, le=1)
    relevance: float = Field(default=0.15, ge=0, le=1)
    depth: float = Field(default=0.15, ge=0, le=1)
    clarity: float = Field(default=0.10, ge=0, le=1)
    project_grounding: float = Field(default=0.10, ge=0, le=1)
    credibility: float = Field(default=0.05, ge=0, le=1)

    @model_validator(mode="after")
    def weights_total_one(self) -> "EvaluationRubric":
        weights = [
            self.correctness, self.completeness, self.relevance, self.depth,
            self.clarity, self.project_grounding, self.credibility,
        ]
        if abs(sum(weights) - 1) > 0.001:
            raise ValueError("评分权重之和必须为 1")
        return self


class EvaluationAgentInput(BaseModel):
    question: InterviewQuestionDraft
    user_answer: str = Field(min_length=1, max_length=20000)
    candidate_profile: CandidateProfile
    retrieved_context: list[SourceRef] = []
    evaluation_rubric: EvaluationRubric = Field(default_factory=EvaluationRubric)
    interview_level: Literal["intern", "junior", "mid", "senior"] = "junior"


class DeterministicEvaluationChecks(BaseModel):
    """Reproducible checks that run before an LLM's qualitative judgment."""

    answer_non_empty: bool
    minimum_length_met: bool
    answer_char_count: int = Field(ge=0)
    expected_point_hits: list[str] = []
    expected_point_coverage: float = Field(ge=0, le=1)
    project_evidence_available: bool


class AnswerEvaluation(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    dimension_scores: DimensionScores
    strengths: list[str] = []
    errors: list[EvaluationIssue] = []
    missing_points: list[str] = []
    improvement_advice: list[str] = []
    answer_framework: list[str] = []
    improved_answer: str = Field(min_length=1, max_length=10000)
    practice_questions: list[str] = []
    confidence: float = Field(ge=0, le=1)
    deterministic_checks: DeterministicEvaluationChecks | None = None

    def recompute_score(self, rubric: EvaluationRubric) -> int:
        score = self.dimension_scores
        project_score = score.project_grounding
        if project_score is None:
            non_project_weight = 1 - rubric.project_grounding
            raw = (
                score.correctness * rubric.correctness
                + score.completeness * rubric.completeness
                + score.relevance * rubric.relevance
                + score.depth * rubric.depth
                + score.clarity * rubric.clarity
                + score.credibility * rubric.credibility
            ) / non_project_weight
        else:
            raw = (
                score.correctness * rubric.correctness
                + score.completeness * rubric.completeness
                + score.relevance * rubric.relevance
                + score.depth * rubric.depth
                + score.clarity * rubric.clarity
                + project_score * rubric.project_grounding
                + score.credibility * rubric.credibility
            )
        return round(raw)
