from app.schemas.eval import EvalResult


def run_judge_eval_placeholder() -> EvalResult:
    return EvalResult(
        score=80,
        passed=True,
        reason="LLM judge eval placeholder. Will be implemented in a later phase.",
    )
