import asyncio

from app.graph.workflow import build_review_graph

EXPECTED_RETRY_COUNT = {
    "context_quality": 0,
    "finding_guardrail": 0,
    "eval_judge": 0,
    "scoring": 0,
}

EXPECTED_FINAL_RESPONSE = {
    "review_mode": "generic",
    "overall_score": 100,
    "confidence": 0,
    "risk_level": "unknown",
    "recommendation": "workflow_skeleton_only",
    "summary": "Workflow skeleton executed successfully.",
    "findings": [],
}

EXPECTED_TRACE = [
    ("S5.1", "parse_pr_url_node"),
    ("S5.2", "fetch_pr_data_node"),
    ("S5.3", "diff_understanding_agent"),
    ("S5.4", "risk_classification_agent"),
    ("S5.5", "rag_query_planner_agent"),
    ("S5.6", "rag_retriever_node"),
    ("S5.7", "context_quality_agent"),
    ("S5.8", "pr_review_agent"),
    ("S5.9", "finding_guardrail_node"),
    ("S5.10", "eval_judge_agent"),
    ("S5.11", "final_scoring_agent"),
    ("S5.12", "response_builder_node"),
]


def _initial_state() -> dict:
    return {
        "request_id": "req_test_skeleton",
        "workflow_mode": "skeleton",
        "pr_url": "https://github.com/abhishek-rahul/sample-payment-service/pull/1",
        "pr_goal": "optional goal",
        "retry_count": EXPECTED_RETRY_COUNT.copy(),
        "errors": [],
        "trace": [],
    }


def _trace_to_dict(item) -> dict:
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return dict(item)


def _run_workflow(state: dict) -> dict:
    return asyncio.run(build_review_graph().ainvoke(state))


def test_workflow_skeleton_runs_offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    async def fail_github_call(*args, **kwargs):
        raise AssertionError("GitHub API should not be called in skeleton mode")

    def fail_real_rag(*args, **kwargs):
        raise AssertionError("Real RAG retrieval should not be called in skeleton mode")

    monkeypatch.setattr("app.graph.nodes.fetch_pr_metadata", fail_github_call)
    monkeypatch.setattr("app.graph.nodes.fetch_changed_files", fail_github_call)
    monkeypatch.setattr("app.rag.retriever.retrieve_context", fail_real_rag)

    result = _run_workflow(_initial_state())

    assert result["final_response"] == EXPECTED_FINAL_RESPONSE
    assert result["workflow_mode"] == "skeleton"
    assert result["retry_count"] == EXPECTED_RETRY_COUNT
    assert result["errors"] == []


def test_workflow_skeleton_trace_contains_all_expected_nodes():
    result = _run_workflow(_initial_state())
    trace = [_trace_to_dict(item) for item in result["trace"]]

    assert [(item["step_id"], item["agent_id"]) for item in trace] == EXPECTED_TRACE
    assert all(item["request_id"] == "req_test_skeleton" for item in trace)
    assert all(item["status"] for item in trace)
    assert all(item["summary"] for item in trace)


def test_workflow_skeleton_state_basics():
    result = _run_workflow(_initial_state())

    assert result["request_id"] == "req_test_skeleton"
    assert result["owner"] == "abhishek-rahul"
    assert result["repo"] == "sample-payment-service"
    assert result["pr_number"] == 1
    assert result["raw_diff"]
    assert result["final_response"] == EXPECTED_FINAL_RESPONSE
