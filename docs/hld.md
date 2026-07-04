# High-Level Design v1

## System boundary

```text
React UI
  -> FastAPI Backend
  -> GitHub API Client
  -> LangGraph Review Workflow
  -> LangChain AI Layer through LLM Gateway
  -> RAG through Embedding Gateway + Elasticsearch
  -> Guardrails + Eval
  -> PostgreSQL later
  -> React UI Result
```

## Important design rules

- Review only current PR changes.
- Use base branch repo context from Elasticsearch.
- Do not report unrelated legacy issues.
- Do not call OpenAI directly inside workflow nodes; use LLM Gateway.
- Do not call OpenAIEmbeddings directly inside RAG code; use Embedding Gateway.
- Every request has `request_id`.
- Every workflow step records `step_id`, `agent_id`, `status`, and `summary`.

## Workflow components

```text
Tool Nodes:
- parse_pr_url_node
- fetch_pr_data_node
- rag_retriever_node

AI / Agent Nodes:
- diff_understanding_agent
- risk_classification_agent
- rag_query_planner_agent
- context_quality_agent
- pr_review_agent
- eval_judge_agent
- final_scoring_agent
- final_response_builder_agent

Guardrail Nodes:
- finding_guardrails_node
- score validation inside final_scoring_agent
```
