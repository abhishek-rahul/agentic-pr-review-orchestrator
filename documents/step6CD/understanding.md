# Step 6C + Step 6D Understanding

## Goal

Step 6C + Step 6D ka goal hai PR review workflow ko zyada reliable banana.

Step 6A/6B tak workflow PR ko samajhta tha, RAG context laata tha, finding banata tha, score deta tha.

Step 6C/6D me extra safety layers add hui:

```text
finding guardrails
finding retry loop
eval judge
eval retry loop
better final scoring
score guardrail
score retry loop
better final response fields
```

Simple words me:

```text
AI finding banata hai.
Guardrail check karta hai ki finding valid hai ya nahi.
Agar invalid hai to AI se dobara better finding banwayi ja sakti hai.
Eval judge review quality check karta hai.
Score guardrail check karta hai ki final score/recommendation sensible hai ya nahi.
```

## What Stayed Same

Ye cheeze intentionally same rakhi gayi:

- Step 5 skeleton final response unchanged.
- `EvalResult.score` unchanged.
- `GuardrailStatus` unchanged.
- `state["guardrail_result"]` still populated.
- `state["guardrails"]` still populated.
- retry keys exactly same:

```python
{
    "context_quality": 0,
    "finding_guardrail": 0,
    "eval_judge": 0,
    "scoring": 0,
}
```

No changes:

- dependencies
- `backend/pyproject.toml`
- FastAPI
- UI
- DB/PostgreSQL
- Alembic
- RAG retriever/indexer signatures
- `retrieve_context_placeholder(...)`

## Main Files Changed

### `backend/app/schemas/eval.py`

New additive schemas added:

```python
GuardrailIssue
FindingGuardrailResult
ScoreBreakdown
ScoreGuardrailResult
```

`EvalResult` was extended additively:

```python
improvement_instruction: str | None
checks: list[str]
```

Important:

```text
EvalResult.score still exists.
Old code using eval_result.score still works.
```

### `backend/app/graph/state.py`

New state fields added:

```python
finding_guardrail_result
review_retry_instruction
eval_improvement_instruction
score_breakdown
score_guardrail_result
scoring_retry_instruction
```

These fields are used only for Step 6C/6D flow.

### `backend/app/graph/nodes.py`

Major updates:

- `finding_guardrail_node` became stronger.
- `eval_judge_agent` now uses LLM Gateway in live mode.
- `final_scoring_agent` got better deterministic scoring.
- new `score_guardrail_node` added.
- `response_builder_node` now includes extra live response fields.

### `backend/app/graph/routers.py`

New retry routers:

```python
route_after_finding_guardrail
route_after_eval
route_after_score_guardrail
```

### `backend/app/graph/workflow.py`

Workflow got new conditional edges:

```text
finding_guardrail -> retry or eval
eval_judge -> retry or scoring
score_guardrail -> retry or response
```

## Live Trace Order

Live successful run trace order:

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
S6D.1 score_guardrail_node
S6A.12 response_builder_node
```

If retry happens, some nodes repeat.

Example finding retry:

```text
S6A.8 pr_review_agent
S6A.9 finding_guardrail_node failed
S6A.8 pr_review_agent
S6A.9 finding_guardrail_node passed
```

## Finding Guardrails

`finding_guardrail_node` checks PR review findings.

It checks:

```text
file path current PR ya retrieved context me hai?
evidence present hai?
issue present hai?
suggestion present hai?
PR relevance present hai?
line_number negative to nahi?
severity calibrated hai?
suggestion generic to nahi?
```

Generic suggestions rejected:

```text
fix this
improve code
add tests
```

Pass result:

```json
{
  "passed": true,
  "issues": [],
  "rejected_finding_indexes": [],
  "retry_instruction": null
}
```

Fail result:

```json
{
  "passed": false,
  "issues": [
    {
      "guardrail_name": "evidence",
      "reason": "Finding is missing required evidence...",
      "finding_index": 0
    }
  ],
  "rejected_finding_indexes": [0],
  "retry_instruction": "Regenerate findings..."
}
```

## Finding Retry Loop

If finding guardrail fails:

```text
route_after_finding_guardrail
-> retry_count["finding_guardrail"] += 1
-> state["review_retry_instruction"] set
-> route back to pr_review_agent
```

Max retry:

```text
3
```

After max retry:

```text
workflow continues to eval_judge_agent
```

## Eval Judge

`eval_judge_agent` checks the quality of final findings.

Live mode:

```text
uses LLM Gateway structured output with EvalResult
```

Fallback:

```text
if LLM fails -> run_rule_eval(...)
```

Eval checks:

```text
findings PR-related?
evidence-backed?
actionable?
severity calibrated?
goal-aware if PR goal exists?
retrieved context used safely?
```

Example:

```json
{
  "score": 85,
  "passed": true,
  "reason": "Findings are PR-related...",
  "improvement_instruction": null,
  "checks": ["Evidence-backed", "Actionable"]
}
```

## Eval Retry Loop

If eval fails:

```text
route_after_eval
-> retry_count["eval_judge"] += 1
-> state["eval_improvement_instruction"] set
-> route back to pr_review_agent
```

If eval passes:

```text
continue to final_scoring_agent
```

## Improved Final Scoring

`final_scoring_agent` calculates:

```python
overall_score
confidence
risk_level
recommendation
score_breakdown
```

Score starts at 100.

Penalties:

```text
critical finding: -30
high finding: -18
medium finding: -8
low finding: -3
high-risk payment/auth/security area with findings: -5
weak context: -8
eval failed or low eval score: -10
finding guardrail failed after max retry: -10
missing tests in high-risk business/payment/security PR: -5
```

Recommendation values:

```text
merge_ready
merge_with_caution
fix_before_merge
needs_human_review
```

## Score Breakdown

`score_breakdown` explains score in simple buckets:

```json
{
  "code_quality": 82,
  "test_coverage": 100,
  "goal_fit": 80,
  "security": 80,
  "architecture_alignment": 82
}
```

## Score Guardrail

New node:

```python
score_guardrail_node
```

Trace:

```text
S6D.1 score_guardrail_node
```

It checks:

```text
overall_score 0-100?
confidence 0-100?
risk_level valid?
recommendation valid?
score_breakdown values 0-100?
high/critical finding with merge_ready? fail
eval failed with very high confidence? fail
weak context with very high confidence? fail
merge_ready score below 85? fail
```

## Score Retry Loop

If score guardrail fails:

```text
route_after_score_guardrail
-> retry_count["scoring"] += 1
-> state["scoring_retry_instruction"] set
-> route back to final_scoring_agent
```

Max retry:

```text
3
```

After max retry:

```text
continue to response_builder_node
```

## Final Response Changes

Old live response keys still exist:

```text
request_id
pr_url
review_mode
overall_score
confidence
risk_level
recommendation
summary
findings
trace
errors
```

New additive live fields:

```text
context_quality
finding_guardrail_result
eval_result
score_guardrail_result
score_breakdown
retry_count
```

Skeleton response does not get these extra fields.

## How To Read A Run Output

### Did fallback happen?

Check:

```json
"errors": []
```

If errors empty, usually no fallback happened.

Eval fallback reason usually looks generic:

```text
Rule-based eval completed...
```

### Did retry happen?

Check:

```json
"retry_count": {
  "finding_guardrail": 2
}
```

If any retry count is greater than 0, retry happened.

Trace also repeats nodes.

### Did guardrails pass?

Check:

```json
"finding_guardrail_result": { "passed": true }
"score_guardrail_result": { "passed": true }
```

### Did eval pass?

Check:

```json
"eval_result": {
  "passed": true,
  "score": 85
}
```
