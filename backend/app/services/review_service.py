from uuid import uuid4

from app.graph.workflow import build_review_graph
from app.schemas.review import ReviewResult


async def review_pr(pr_url: str, pr_goal: str | None, request_id: str | None = None) -> ReviewResult:
    graph = build_review_graph()
    state = await graph.ainvoke(
        {
            "request_id": request_id or str(uuid4()),
            "pr_url": pr_url,
            "pr_goal": pr_goal,
            "trace": [],
        }
    )

    return ReviewResult(
        request_id=state["request_id"],
        review_mode="Goal-aware PR Review" if pr_goal else "Generic PR Review",
        pr_url=pr_url,
        pr_metadata=state["pr_metadata"],
        changed_files=state["changed_files"],
        diff_summary=state["diff_summary"],
        risk_summary=state["risk_summary"],
        rag_query_plan=state["rag_query_plan"],
        retrieved_context=state["retrieved_context"],
        context_quality=state["context_quality"],
        overall_score=state["overall_score"],
        confidence=state["confidence"],
        risk_level=state["risk_level"],
        recommendation=state["recommendation"],
        final_summary=state["final_summary"],
        findings=state["findings"],
        guardrails=state["guardrails"],
        eval_result=state["eval_result"],
        trace=state["trace"],
    )
