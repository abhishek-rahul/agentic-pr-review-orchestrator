from app.graph.nodes import (
    context_quality_agent,
    diff_understanding_agent,
    eval_judge_agent,
    final_response_builder_agent,
    final_scoring_agent,
    finding_guardrails_node,
    pr_review_agent,
    rag_query_planner_agent,
    rag_retriever_node,
    risk_classification_agent,
)
from app.schemas.pr import ChangedFile


def test_basic_node_flow_without_github_call():
    state = {
        "request_id": "test-request-1",
        "workflow_mode": "skeleton",
        "pr_url": "https://github.com/org/repo/pull/1",
        "pr_goal": None,
        "changed_files": [ChangedFile(filename="app/service.py", status="modified")],
        "trace": [],
    }

    state = diff_understanding_agent(state)
    state = risk_classification_agent(state)
    state = rag_query_planner_agent(state)
    state = rag_retriever_node(state)
    state = context_quality_agent(state)
    state = pr_review_agent(state)
    state = finding_guardrails_node(state)
    state = eval_judge_agent(state)
    state = final_scoring_agent(state)
    state = final_response_builder_agent(state)

    assert state["overall_score"] <= 100
    assert state["guardrails"].pr_scope_passed
    assert state["final_summary"]
    assert state["trace"]
