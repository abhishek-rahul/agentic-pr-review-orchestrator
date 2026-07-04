# LangGraph Workflow Flow

## Final planned sequence

```text
S6.1  parse_pr_url_node
S6.2  fetch_pr_data_node
S6.3  diff_understanding_agent
S6.4  risk_classification_agent
S6.5  rag_query_planner_agent
S6.6  rag_retriever_node
S6.7  context_quality_agent
S6.8  pr_review_agent
S6.9  finding_guardrails_node
S6.10 eval_judge_agent
S6.11 final_scoring_agent
S6.12 final_response_builder_agent
```

## Current implementation status

This repository is now prepared as a development starting point. Some agents still use simple deterministic placeholder logic. Replace those placeholders step by step during development.

## Debug trace contract

Every node must call:

```python
add_trace(state, step_id, agent_id, status, summary)
```

Each trace item has:

```text
request_id
step_id
agent_id
status
summary
```
