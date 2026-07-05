# Step 6A Function Call Flow

## Big Picture

Step 6A workflow LangGraph pipeline se run hota hai.

Entry point:

```text
backend/scripts/run_workflow.py
```

Graph builder:

```text
backend/app/graph/workflow.py
```

Node implementations:

```text
backend/app/graph/nodes.py
```

Flow:

```text
run_workflow.py
-> build_review_graph()
-> graph.ainvoke(initial_state)
-> parse_pr_url_node
-> fetch_pr_data_node
-> diff_understanding_agent
-> risk_classification_agent
-> rag_query_planner_agent
-> rag_retriever_node
-> context_quality_agent
-> pr_review_agent
-> finding_guardrail_node
-> eval_judge_agent
-> final_scoring_agent
-> response_builder_node
-> final_response
```

## Initial State

Runner initial state banata hai:

```python
{
    "request_id": "req_xxx",
    "workflow_mode": "skeleton" or "live",
    "pr_url": "...",
    "pr_goal": "...",
    "retry_count": {
        "context_quality": 0,
        "finding_guardrail": 0,
        "eval_judge": 0,
        "scoring": 0,
    },
    "errors": [],
    "trace": [],
}
```

Ye state har node me pass hoti hai. Har node isi state ko read/update karta hai.

## Workflow Mode Decision

Helper:

```python
_workflow_mode(state)
```

Behavior:

```text
if state["workflow_mode"] exists -> use it
else -> live
```

Meaning:

- Runner default skeleton deta hai.
- Tests explicit live/skeleton pass karte hain.
- Agar kisi future caller ne mode nahi diya, nodes live maanenge.

## Trace ID Decision

Helper:

```python
_step_id(state, skeleton_id, live_id)
```

Example:

```python
_step_id(state, "S5.1", "S6A.1")
```

Skeleton mode:

```text
S5.1
```

Live mode:

```text
S6A.1
```

Har node `add_trace(...)` call karta hai.

Trace item shape:

```json
{
  "request_id": "...",
  "step_id": "...",
  "agent_id": "...",
  "status": "...",
  "summary": "..."
}
```

## Detailed Node Flow

## 1. `parse_pr_url_node`

Input state:

```python
state["pr_url"]
```

Call:

```python
parse_pr_url(state["pr_url"])
```

Output state:

```python
state["pr_ref"]
state["owner"]
state["repo"]
state["pr_number"]
```

Trace:

```text
S5.1 or S6A.1
agent_id=parse_pr_url_node
```

Simple meaning:

GitHub URL ko owner, repo, PR number me todta hai.

## 2. `fetch_pr_data_node`

Input state:

```python
state["pr_ref"]
```

Skeleton mode:

```text
dummy metadata
dummy changed file
dummy raw diff
```

No external call.

Live mode calls:

```python
fetch_pr_metadata(pr_ref)
fetch_changed_files(pr_ref)
```

Output state:

```python
state["pr_metadata"]
state["changed_files"]
state["raw_diff"]
```

Raw diff:

```python
"\n".join(file.patch or "" for file in changed_files)
```

If GitHub fails:

```python
_append_error(state, "S6A.2", "fetch_pr_data_node", str(exc))
raise RuntimeError(...)
```

Simple meaning:

Live PR ka title, author, branch, changed files, patch data fetch karta hai.

## 3. `diff_understanding_agent`

Skeleton mode:

```python
_deterministic_diff_summary(state)
```

Live mode:

```python
_get_structured_llm(DiffSummary).invoke(_diff_prompt(state))
```

If LLM fails:

```python
_append_error(state, "S6A.3", "diff_understanding_agent", str(exc))
_deterministic_diff_summary(state)
```

Output state:

```python
state["diff_summary"]
```

Simple meaning:

PR me kis type ka change hai ye samajhta hai:

- docs
- tests
- config
- business logic
- mixed

## 4. `risk_classification_agent`

Skeleton mode:

```python
_deterministic_risk_summary(state)
```

Live mode:

```python
_get_structured_llm(RiskSummary).invoke(_risk_prompt(state))
```

If LLM fails:

```python
_append_error(state, "S6A.4", "risk_classification_agent", str(exc))
_deterministic_risk_summary(state)
```

Output state:

```python
state["risk_summary"]
```

Simple meaning:

PR ka risk decide karta hai:

- low
- medium
- high
- critical

## 5. `rag_query_planner_agent`

Skeleton mode:

Existing placeholder query plan.

Live mode:

```python
state["rag_query_plan"] = RAGQueryPlan(queries=[], top_k=0)
```

Trace:

```text
S6A.5 skipped RAG planning skipped in Step 6A
```

Simple meaning:

Step 6A me RAG planning intentionally disabled hai.

## 6. `rag_retriever_node`

Skeleton mode:

Uses:

```python
retrieve_context_placeholder(...)
```

Live mode:

```python
state["retrieved_context"] = []
```

Trace:

```text
S6A.6 skipped RAG retrieval skipped in Step 6A
```

Simple meaning:

Live mode me Elasticsearch retrieval abhi nahi hota.

## 7. `context_quality_agent`

Skeleton mode:

Existing placeholder context quality logic.

Live mode:

```python
ContextQualityResult(
    context_enough=True,
    reason="RAG context quality check skipped in Step 6A.",
    missing_context=[],
    suggested_queries=[],
)
```

Simple meaning:

RAG skip hai, isliye context quality bhi placeholder hai.

## 8. `pr_review_agent`

Skeleton mode:

Existing deterministic placeholder findings.

Live mode:

```python
_get_structured_llm(FindingList).invoke(_review_prompt(state)).findings
```

If LLM fails:

```python
_append_error(state, "S6A.8", "pr_review_agent", str(exc))
_fallback_findings(state)
```

Output state:

```python
state["findings"]
```

Simple meaning:

AI findings banata hai. Agar AI fail ho jaye to basic fallback findings use hote hain.

Fallback cases:

```text
source file changed + no test file -> missing test finding
validation removed -> high risk validation finding
```

## 9. `finding_guardrail_node`

Input:

```python
state["findings"]
state["changed_files"]
```

Calls:

```python
validate_pr_scope(findings, changed_files)
validate_evidence(findings)
validate_file_paths(findings, changed_files)
```

Output:

```python
state["guardrail_result"]
state["guardrails"]
```

Simple meaning:

Basic check karta hai ki finding PR se related hai ya hallucinated nahi hai.

## 10. `eval_judge_agent`

Calls:

```python
run_rule_eval(findings, guardrail_result)
```

Output:

```python
state["eval_result"]
```

Simple meaning:

Abhi simple rule-based eval hai. LLM judge nahi hai.

## 11. `final_scoring_agent`

Input:

```python
state["risk_summary"]
state["findings"]
state["guardrail_result"]
state["eval_result"]
```

Live mode scoring:

```text
base score risk se aata hai
finding severity se penalty lagti hai
guardrail fail ho to score cap hota hai
```

Output:

```python
state["overall_score"]
state["confidence"]
state["risk_level"]
state["recommendation"]
state["score_result"]
```

Recommendation logic:

```text
score high + no high finding -> merge_ready
score 70-84 -> merge_with_caution
score 40-69 -> fix_before_merge
score < 40 -> needs_human_review
```

Simple meaning:

PR review ka final score and decision banata hai.

## 12. `response_builder_node`

Skeleton mode:

Fixed dummy response.

Live mode:

1. Summary build hoti hai.
2. `S6A.12` trace add hota hai.
3. Trace serialize hota hai.
4. Final JSON response build hota hai.

Output:

```python
state["final_response"]
```

Final response shape:

```json
{
  "request_id": "...",
  "pr_url": "...",
  "review_mode": "...",
  "overall_score": 82,
  "confidence": 75,
  "risk_level": "medium",
  "recommendation": "merge_with_caution",
  "summary": "...",
  "findings": [],
  "trace": [],
  "errors": []
}
```

Simple meaning:

Internal state ko clean response me convert karta hai.

## LLM Gateway Flow

Graph node direct `ChatOpenAI` create nahi karta.

Flow:

```text
nodes.py
-> _get_structured_llm(schema)
-> get_llm()
-> model.with_structured_output(schema)
-> invoke(prompt)
```

Why:

- LLM config one place me rahe.
- Tests easily monkeypatch kar sake.
- Graph nodes OpenAI-specific na ho.

## Error Flow

Error helper:

```python
_append_error(state, step_id, agent_id, message)
```

Error item shape:

```json
{
  "step_id": "S6A.8",
  "agent_id": "pr_review_agent",
  "message": "Force review fallback"
}
```

Important:

- No timestamp.
- No stack trace.
- No extra metadata.

## Business Logic Without Tests Flow

Test setup:

```text
changed file: app/payment_service.py
no test file
review LLM fails intentionally
```

Call flow:

```text
pr_review_agent
-> _get_structured_llm(FindingList).invoke(...)
-> raises RuntimeError
-> _append_error(S6A.8, pr_review_agent, ...)
-> _fallback_findings(state)
-> missing_test_for_changed_logic finding
```

Expected final response:

```text
finding severity medium
relation_to_pr missing_test_for_changed_logic
file_path app/payment_service.py
errors contains S6A.8 pr_review_agent
```

## Good Test-Only PR Flow

Test setup:

```text
changed file: tests/test_discount_policy.py
LLM diff: test_change
LLM risk: low
LLM findings: []
```

Call flow:

```text
diff_understanding_agent -> test_change
risk_classification_agent -> low
pr_review_agent -> []
final_scoring_agent -> high score
response_builder_node -> merge_ready response
```

Expected final response:

```text
findings []
risk_level low
overall_score >= 85
recommendation merge_ready
errors []
```

## Trace Flow

Live trace should always be:

```text
S6A.1 parse_pr_url_node
S6A.2 fetch_pr_data_node
S6A.3 diff_understanding_agent
S6A.4 risk_classification_agent
S6A.5 rag_query_planner_agent
S6A.6 rag_retriever_node
S6A.7 context_quality_agent
S6A.8 pr_review_agent
S6A.9 finding_guardrail_node
S6A.10 eval_judge_agent
S6A.11 final_scoring_agent
S6A.12 response_builder_node
```

Skeleton trace should always be:

```text
S5.1 to S5.12
```

## What To Remember

Step 6A is a basic live review MVP.

The safest mental model:

```text
GitHub PR data
-> structured AI summaries
-> basic findings
-> basic scoring
-> JSON response
```

And equally important:

```text
No real RAG yet
No DB save yet
No UI yet
No production review quality claim yet
```
