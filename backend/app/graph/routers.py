from app.graph.state import PRReviewState


def route_after_context_quality(state: PRReviewState) -> str:
    if state["context_quality"].context_enough:
        return "pr_review"
    return "rag_query_planner"


def route_after_finding_guardrails(state: PRReviewState) -> str:
    guardrails = state["guardrails"]
    if guardrails.pr_scope_passed and guardrails.evidence_passed and guardrails.hallucination_passed:
        return "eval_judge"
    return "pr_review"


def route_after_eval(state: PRReviewState) -> str:
    if state["eval_result"].passed:
        return "final_scoring"
    return "pr_review"
