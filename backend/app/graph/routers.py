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


def route_after_finding_guardrail(state: PRReviewState) -> str:
    if state.get("workflow_mode") == "skeleton":
        return "eval_judge"

    result = state.get("finding_guardrail_result")
    if result and result.passed:
        print("[finding_router] route=eval_judge retry_count=0")
        return "eval_judge"

    retry_count = state.setdefault("retry_count", {})
    current_retry = retry_count.get("finding_guardrail", 0)
    if current_retry < 3:
        retry_count["finding_guardrail"] = current_retry + 1
        state["review_retry_instruction"] = (
            result.retry_instruction if result and result.retry_instruction else "Regenerate review findings."
        )
        print(f"[finding_router] route=pr_review retry_count={retry_count['finding_guardrail']}")
        return "pr_review"

    print(f"[finding_router] route=eval_judge retry_count={current_retry}")
    return "eval_judge"


def route_after_eval(state: PRReviewState) -> str:
    if state.get("workflow_mode") == "skeleton":
        return "final_scoring"

    result = state.get("eval_result")
    if result and result.passed:
        print("[eval_router] route=final_scoring retry_count=0")
        return "final_scoring"

    retry_count = state.setdefault("retry_count", {})
    current_retry = retry_count.get("eval_judge", 0)
    if current_retry < 3:
        retry_count["eval_judge"] = current_retry + 1
        state["eval_improvement_instruction"] = (
            result.improvement_instruction if result and result.improvement_instruction else "Improve findings quality."
        )
        print(f"[eval_router] route=pr_review retry_count={retry_count['eval_judge']}")
        return "pr_review"

    print(f"[eval_router] route=final_scoring retry_count={current_retry}")
    return "final_scoring"


def route_after_scoring(state: PRReviewState) -> str:
    return "response_builder"


def route_after_score_guardrail(state: PRReviewState) -> str:
    if state.get("workflow_mode") == "skeleton":
        return "response_builder"

    result = state.get("score_guardrail_result")
    if result and result.passed:
        print("[score_router] route=response_builder retry_count=0")
        return "response_builder"

    retry_count = state.setdefault("retry_count", {})
    current_retry = retry_count.get("scoring", 0)
    if current_retry < 3:
        retry_count["scoring"] = current_retry + 1
        state["scoring_retry_instruction"] = (
            result.retry_instruction if result and result.retry_instruction else "Recalculate score consistently."
        )
        print(f"[score_router] route=final_scoring retry_count={retry_count['scoring']}")
        return "final_scoring"

    print(f"[score_router] route=response_builder retry_count={current_retry}")
    return "response_builder"


route_after_finding_guardrails = route_after_finding_guardrail
