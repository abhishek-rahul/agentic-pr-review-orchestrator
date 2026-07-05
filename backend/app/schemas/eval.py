from pydantic import BaseModel
from pydantic import Field


class GuardrailStatus(BaseModel):
    pr_scope_passed: bool
    evidence_passed: bool
    hallucination_passed: bool
    score_passed: bool


class GuardrailIssue(BaseModel):
    guardrail_name: str
    reason: str
    finding_index: int | None = None


class FindingGuardrailResult(BaseModel):
    passed: bool
    issues: list[GuardrailIssue] = Field(default_factory=list)
    rejected_finding_indexes: list[int] = Field(default_factory=list)
    retry_instruction: str | None = None


class EvalResult(BaseModel):
    score: int
    passed: bool
    reason: str
    improvement_instruction: str | None = None
    checks: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    code_quality: int
    test_coverage: int
    goal_fit: int
    security: int
    architecture_alignment: int


class ScoreGuardrailResult(BaseModel):
    passed: bool
    issues: list[GuardrailIssue] = Field(default_factory=list)
    retry_instruction: str | None = None
