from langgraph.graph import END, START, StateGraph

from app.graph.routers import route_after_context_quality
from app.graph.nodes import (
    context_quality_agent,
    diff_understanding_agent,
    eval_judge_agent,
    fetch_pr_data_node,
    final_scoring_agent,
    finding_guardrail_node,
    parse_pr_url_node,
    pr_review_agent,
    rag_query_planner_agent,
    rag_retriever_node,
    response_builder_node,
    risk_classification_agent,
)
from app.graph.state import PRReviewState


def build_review_graph():
    graph = StateGraph(PRReviewState)

    graph.add_node("parse_pr_url", parse_pr_url_node)
    graph.add_node("fetch_pr_data", fetch_pr_data_node)
    graph.add_node("diff_understanding", diff_understanding_agent)
    graph.add_node("risk_classification", risk_classification_agent)
    graph.add_node("rag_query_planner", rag_query_planner_agent)
    graph.add_node("rag_retriever", rag_retriever_node)
    graph.add_node("context_quality", context_quality_agent)
    graph.add_node("pr_review", pr_review_agent)
    graph.add_node("finding_guardrail", finding_guardrail_node)
    graph.add_node("eval_judge", eval_judge_agent)
    graph.add_node("final_scoring", final_scoring_agent)
    graph.add_node("response_builder", response_builder_node)

    graph.add_edge(START, "parse_pr_url")
    graph.add_edge("parse_pr_url", "fetch_pr_data")
    graph.add_edge("fetch_pr_data", "diff_understanding")
    graph.add_edge("diff_understanding", "risk_classification")
    graph.add_edge("risk_classification", "rag_query_planner")
    graph.add_edge("rag_query_planner", "rag_retriever")
    graph.add_edge("rag_retriever", "context_quality")
    graph.add_conditional_edges(
        "context_quality",
        route_after_context_quality,
        {
            "rag_query_planner": "rag_query_planner",
            "pr_review": "pr_review",
        },
    )
    graph.add_edge("pr_review", "finding_guardrail")
    graph.add_edge("finding_guardrail", "eval_judge")
    graph.add_edge("eval_judge", "final_scoring")
    graph.add_edge("final_scoring", "response_builder")
    graph.add_edge("response_builder", END)

    return graph.compile()
