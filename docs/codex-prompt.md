# Codex Prompt

Use this prompt when asking Codex to continue development.

```text
You are working on Agentic PR Review & Code Quality Orchestrator.

Goal:
Build the project step by step according to docs/development-phases.md and docs/flow.md.

Hard rules:
1. Keep code simple and easy to understand.
2. Do not add unnecessary classes, factories, managers, or large dictionaries.
3. Do not change dependency versions unless explicitly asked.
4. Do not remove existing project docs.
5. Do not hardcode ChatOpenAI or OpenAIEmbeddings inside agents. Use app/ai gateways.
6. Every workflow node must add debug trace using add_trace.
7. Every trace item must include request_id, step_id, agent_id, status, summary.
8. Every AI node output must use a Pydantic schema before going into LangGraph state.
9. Review only current PR changes. Do not report unrelated legacy codebase issues.
10. Prefer small functions over large classes.

Current workflow order:
S6.1 parse_pr_url_node
S6.2 fetch_pr_data_node
S6.3 diff_understanding_agent
S6.4 risk_classification_agent
S6.5 rag_query_planner_agent
S6.6 rag_retriever_node
S6.7 context_quality_agent
S6.8 pr_review_agent
S6.9 finding_guardrails_node
S6.10 eval_judge_agent
S6.11 final_scoring_agent
S6.12 final_response_builder_agent

Before modifying code:
- Read docs/hld.md
- Read docs/flow.md
- Read docs/development-phases.md
- Read docs/agent-rules.md

After modifying code:
- Run backend tests if dependencies are installed
- Do not introduce dependency conflicts
```
