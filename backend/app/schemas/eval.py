from pydantic import BaseModel


class GuardrailStatus(BaseModel):
    pr_scope_passed: bool
    evidence_passed: bool
    hallucination_passed: bool
    score_passed: bool


class EvalResult(BaseModel):
    score: int
    passed: bool
    reason: str
