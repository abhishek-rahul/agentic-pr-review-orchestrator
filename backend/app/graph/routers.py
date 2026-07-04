from app.graph.state import PRReviewState


def route_after_context_quality(state: PRReviewState) -> str:
    return "pr_review"


def route_after_guardrails(state: PRReviewState) -> str:
    return "eval_judge"


def route_after_eval(state: PRReviewState) -> str:
    return "final_scoring"


def route_after_scoring(state: PRReviewState) -> str:
    return "response_builder"


route_after_finding_guardrails = route_after_guardrails
