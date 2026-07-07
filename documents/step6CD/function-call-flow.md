# Step 6C + Step 6D Function Call Flow

## Scope

This doc explains only Step 6C/6D function flow.

It does not repeat full Step 6A/6B internals except where needed.

Step 6C/6D starts after:

```text
pr_review_agent creates findings
```

Then new safety flow begins:

```text
finding_guardrail_node
-> route_after_finding_guardrail
-> eval_judge_agent
-> route_after_eval
-> final_scoring_agent
-> score_guardrail_node
-> route_after_score_guardrail
-> response_builder_node
```

## High-Level Flow

```text
pr_review_agent
-> finding_guardrail_node
   -> if failed and retry < 3:
      -> pr_review_agent again
   -> else:
      -> eval_judge_agent

eval_judge_agent
-> if failed and retry < 3:
   -> pr_review_agent again
-> else:
   -> final_scoring_agent

final_scoring_agent
-> score_guardrail_node
   -> if failed and retry < 3:
      -> final_scoring_agent again
   -> else:
      -> response_builder_node
```

## 1. pr_review_agent Prompt Change

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
pr_review_agent(state)
```

Step 6C/6D added these prompt inputs:

```python
state["review_retry_instruction"]
state["eval_improvement_instruction"]
```

Flow:

```text
pr_review_agent
-> _review_prompt(state)
   -> includes review_retry_instruction
   -> includes eval_improvement_instruction
-> _get_structured_llm(FindingList)
-> findings
```

Why:

```text
If guardrail/eval failed earlier, reviewer gets instruction on what to fix.
```

## 2. finding_guardrail_node

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
finding_guardrail_node(state)
```

Function call flow:

```text
finding_guardrail_node(state)
-> findings = state["findings"]
-> changed_files = state["changed_files"]
-> _run_finding_guardrails(state)
-> validate_pr_scope(findings, changed_files)
-> validate_evidence(findings)
-> validate_file_paths(findings, changed_files)
-> state["guardrail_result"]
-> state["guardrails"]
-> state["finding_guardrail_result"]
-> add_trace(S6A.9)
```

Compatibility:

```text
state["guardrail_result"] still exists
state["guardrails"] still exists
```

New detailed result:

```python
state["finding_guardrail_result"]
```

## 3. _run_finding_guardrails

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
_run_finding_guardrails(state)
```

Checks every finding:

```text
file_path allowed?
issue present?
suggestion present?
evidence present?
PR relevance present?
line_number non-negative?
severity calibrated?
suggestion specific enough?
```

Allowed file paths:

```text
changed files
retrieved context files
```

If fail:

```text
create GuardrailIssue
add finding index to rejected_finding_indexes
set retry_instruction
```

Return:

```python
FindingGuardrailResult
```

## 4. route_after_finding_guardrail

File:

```text
backend/app/graph/routers.py
```

Function:

```python
route_after_finding_guardrail(state)
```

Flow:

```text
if skeleton:
    eval_judge

if finding_guardrail_result.passed:
    eval_judge

if failed and retry_count["finding_guardrail"] < 3:
    retry_count["finding_guardrail"] += 1
    state["review_retry_instruction"] = retry_instruction
    pr_review

else:
    eval_judge
```

This is the finding retry loop.

## 5. eval_judge_agent

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
eval_judge_agent(state)
```

Live flow:

```text
eval_judge_agent
-> _eval_prompt(state)
-> _get_structured_llm(EvalResult)
-> llm.invoke(prompt)
-> state["eval_result"]
-> add_trace(S6A.10)
```

Fallback flow:

```text
if LLM fails:
    _append_error(...)
    run_rule_eval(findings, guardrail_result)
```

It does not store raw LLM text.

It keeps:

```python
eval_result.score
eval_result.passed
eval_result.reason
```

## 6. _eval_prompt

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
_eval_prompt(state)
```

Prompt includes:

```text
PR goal
changed files
diff summary
risk summary
context quality
retrieved context summary
finding guardrail result
findings
trimmed diff
```

Purpose:

```text
Judge if review findings are relevant, evidence-backed, actionable, and severity calibrated.
```

## 7. route_after_eval

File:

```text
backend/app/graph/routers.py
```

Function:

```python
route_after_eval(state)
```

Flow:

```text
if skeleton:
    final_scoring

if eval_result.passed:
    final_scoring

if failed and retry_count["eval_judge"] < 3:
    retry_count["eval_judge"] += 1
    state["eval_improvement_instruction"] = improvement_instruction
    pr_review

else:
    final_scoring
```

This is the eval retry loop.

## 8. final_scoring_agent

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
final_scoring_agent(state)
```

Live scoring flow:

```text
score = 100
subtract finding penalties
subtract high-risk area penalty
subtract weak context penalty
subtract eval failure penalty
subtract failed guardrail after max retry penalty
subtract missing-test high-risk penalty
clamp 0-100
calculate confidence
calculate risk_level
calculate recommendation
build score_breakdown
state["score_result"]
add_trace(S6A.11)
```

Finding penalties:

```text
critical -30
high -18
medium -8
low -3
```

Recommendation values:

```text
merge_ready
merge_with_caution
fix_before_merge
needs_human_review
```

## 9. _build_score_breakdown

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
_build_score_breakdown(state, score)
```

Creates:

```python
ScoreBreakdown(
    code_quality=...,
    test_coverage=...,
    goal_fit=...,
    security=...,
    architecture_alignment=...,
)
```

Purpose:

```text
Explain final score in smaller buckets.
```

## 10. score_guardrail_node

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
score_guardrail_node(state)
```

Skeleton mode:

```text
sets score_guardrail_result passed
does not add trace
```

Live mode:

```text
score_guardrail_node
-> _run_score_guardrails(state)
-> state["score_guardrail_result"]
-> update guardrail_result.score_passed
-> update state["guardrails"]
-> add_trace(S6D.1)
```

## 11. _run_score_guardrails

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
_run_score_guardrails(state)
```

Checks:

```text
overall_score 0-100?
confidence 0-100?
risk_level valid?
recommendation valid?
score_breakdown values 0-100?
high/critical finding with merge_ready?
failed eval with very high confidence?
weak context with very high confidence?
needs_human_review with very high score?
merge_ready with score below 85?
```

Return:

```python
ScoreGuardrailResult
```

## 12. route_after_score_guardrail

File:

```text
backend/app/graph/routers.py
```

Function:

```python
route_after_score_guardrail(state)
```

Flow:

```text
if skeleton:
    response_builder

if score_guardrail_result.passed:
    response_builder

if failed and retry_count["scoring"] < 3:
    retry_count["scoring"] += 1
    state["scoring_retry_instruction"] = retry_instruction
    final_scoring

else:
    response_builder
```

This is the score retry loop.

## 13. response_builder_node Additive Fields

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
response_builder_node(state)
```

Live final response now includes old fields plus:

```text
context_quality
finding_guardrail_result
eval_result
score_guardrail_result
score_breakdown
retry_count
```

Skeleton final response unchanged.

## Step 6C/6D Changed Flow Summary

```text
pr_review_agent
-> finding_guardrail_node
   -> _run_finding_guardrails
   -> route_after_finding_guardrail
      -> retry pr_review_agent if needed

-> eval_judge_agent
   -> _eval_prompt
   -> LLM Gateway EvalResult
   -> route_after_eval
      -> retry pr_review_agent if needed

-> final_scoring_agent
   -> _build_score_breakdown

-> score_guardrail_node
   -> _run_score_guardrails
   -> route_after_score_guardrail
      -> retry final_scoring_agent if needed

-> response_builder_node
```

## How To Read Trace For Retry

No retry:

```text
S6A.8
S6A.9
S6A.10
S6A.11
S6D.1
S6A.12
```

Finding retry:

```text
S6A.8
S6A.9 failed
S6A.8
S6A.9 passed
```

Eval retry:

```text
S6A.10 failed
S6A.8
S6A.9
S6A.10 passed
```

Score retry:

```text
S6A.11
S6D.1 failed
S6A.11
S6D.1 passed
```

## Simple Mental Model

```text
Finding guardrail checks the review findings.
Eval judge checks the review quality.
Score guardrail checks final score consistency.
Routers retry only the part that can fix the issue.
```
