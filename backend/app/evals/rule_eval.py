from app.schemas.eval import EvalResult, GuardrailStatus
from app.schemas.finding import Finding


def run_rule_eval(findings: list[Finding], guardrails: GuardrailStatus) -> EvalResult:
    checks = [
        guardrails.pr_scope_passed,
        guardrails.evidence_passed,
        guardrails.hallucination_passed,
        guardrails.score_passed,
    ]
    base_score = int((sum(checks) / len(checks)) * 100)

    if findings:
        useful_score = min(100, base_score)
    else:
        useful_score = max(70, base_score - 10)

    return EvalResult(
        score=useful_score,
        passed=useful_score >= 70,
        reason="Rule-based eval completed for PR scope, evidence, hallucination, and score.",
    )
