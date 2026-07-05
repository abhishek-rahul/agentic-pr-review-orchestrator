from app.graph.state import PRReviewState


def route_after_context_quality(state: PRReviewState) -> str:
    if state.get("workflow_mode") == "skeleton":
        return "pr_review"

    context_quality = state.get("context_quality")
    if context_quality and context_quality.context_enough:
        return "pr_review"

    retry_count = state.setdefault("retry_count", {})
    current_retry = retry_count.get("context_quality", 0)
    if current_retry < 3:
        retry_count["context_quality"] = current_retry + 1
        print("[context_router] route=rag_query_planner")
        return "rag_query_planner"

    print("[context_router] route=pr_review")
    return "pr_review"


def route_after_guardrails(state: PRReviewState) -> str:
    return "eval_judge"


def route_after_eval(state: PRReviewState) -> str:
    return "final_scoring"


def route_after_scoring(state: PRReviewState) -> str:
    return "response_builder"


route_after_finding_guardrails = route_after_guardrails
