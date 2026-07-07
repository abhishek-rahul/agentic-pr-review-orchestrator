# Step 6C + Step 6D Testing Guide

## Goal

Is guide ka goal hai Step 6C/6D changes ko simple steps me test karna.

Hum test karenge:

```text
skeleton unchanged hai
finding guardrails kaam kar rahe hain
finding retry kaam kar raha hai
eval judge kaam kar raha hai
eval retry kaam kar raha hai
final scoring sensible hai
score guardrail kaam kar raha hai
score retry kaam kar raha hai
live final response me additive fields aa rahe hain
```

## 1. Backend Folder Me Jao

PowerShell:

```powershell
cd C:\gitcode\ai_agents\develop\agentic-pr-review-orchestrator\backend
```

Git Bash:

```bash
cd /c/gitcode/ai_agents/develop/agentic-pr-review-orchestrator/backend
```

## 2. Virtual Env Activate Karo

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Git Bash:

```bash
source .venv/Scripts/activate
```

## 3. Focused Offline Test Command

Command:

```bash
python -B -m pytest -p no:cacheprovider tests/test_workflow.py tests/test_workflow_skeleton.py tests/test_workflow_live_basic.py tests/test_guardrail_retry_flow.py tests/test_scoring_guardrail.py
```

Expected:

```text
35 passed
```

Ye command real OpenAI/GitHub/Elasticsearch/Docker nahi call karta.

## 4. Is Command Me Kya Test Ho Raha Hai

### `tests/test_workflow.py`

Basic node flow still works.

Expected:

```text
old compatibility aliases still work
final summary exists
guardrails exist
```

### `tests/test_workflow_skeleton.py`

Step 5 skeleton unchanged hai.

Expected:

```text
final_response exact dummy response
trace S5.1 to S5.12
no GitHub/OpenAI/Elasticsearch call
```

### `tests/test_workflow_live_basic.py`

Step 6A/6B live mocked flow still works plus Step 6D trace included.

Expected trace:

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

Expected live response fields:

```text
old fields still present
context_quality present
finding_guardrail_result present
eval_result present
score_guardrail_result present
score_breakdown present
retry_count present
```

### `tests/test_guardrail_retry_flow.py`

Tests:

```text
PR scope guardrail pass/fail
evidence guardrail fail
hallucination guardrail fail
severity guardrail fail
suggestion guardrail fail
finding retry router
finding max retry router
mocked eval judge
eval retry router
eval max retry router
```

Expected:

```text
bad finding fails guardrail
router retries up to 3
eval can route back to pr_review_agent
```

### `tests/test_scoring_guardrail.py`

Tests:

```text
high/medium finding scoring
critical finding recommendation
score guardrail pass
score guardrail fail
score retry router
```

Expected:

```text
high finding cannot be merge_ready
critical finding needs human review
bad score recommendation fails guardrail
score retry increments retry_count["scoring"]
```

## 5. Full Pytest

Try:

```bash
python -B -m pytest -p no:cacheprovider --basetemp ./.pytest-tmp-step6cd
```

Ideal expected:

```text
all tests pass
```

Known local issue:

On this Windows environment, full pytest may fail with:

```text
PermissionError: [WinError 5]
```

This happens while pytest creates temp folders for `tests/test_rag_indexing.py`.

If focused suite passes and only temp permission errors remain, Step 6C/6D logic is still verified.

## 6. Compile Check

Normal:

```bash
python -B -m compileall app
```

If pycache permission issue aaye:

PowerShell:

```powershell
$env:PYTHONPYCACHEPREFIX="C:\tmp\agentic-pr-pycache-step6cd"
python -B -m compileall app
```

Expected:

```text
compileall completes without syntax errors
```

## 7. Manual Skeleton Test

Command:

```bash
python -B scripts/run_workflow.py --workflow-mode skeleton --pr-url "https://github.com/abhishek-rahul/sample-payment-service/pull/1"
```

Expected final response:

```json
{
  "review_mode": "generic",
  "overall_score": 100,
  "confidence": 0,
  "risk_level": "unknown",
  "recommendation": "workflow_skeleton_only",
  "summary": "Workflow skeleton executed successfully.",
  "findings": []
}
```

Meaning:

```text
Step 5 skeleton unchanged hai.
```

## 8. Manual Live Test - Docs PR

Command:

```bash
python -B scripts/run_workflow.py --workflow-mode live --print-state --pr-url "https://github.com/abhishek-rahul/sample-payment-service/pull/1"
```

Expected:

```text
docs_change
risk low
finding guardrail pass
eval pass
score guardrail pass
retry_count all zero
recommendation merge_ready
```

## 9. Manual Live Test - Business Logic Missing Tests

Command:

```bash
python -B scripts/run_workflow.py --workflow-mode live --print-state --pr-url "https://github.com/abhishek-rahul/sample-payment-service/pull/2"
```

Expected:

```text
business_logic_change
finding around processing_fee
possible finding_guardrail retry
eval pass after final good findings
score guardrail pass
recommendation fix_before_merge
```

How to know retry happened:

```json
"retry_count": {
  "finding_guardrail": 2
}
```

Trace will show repeated:

```text
S6A.8 pr_review_agent
S6A.9 finding_guardrail_node
```

## 10. Manual Live Test - Coupon Bug

Command:

```bash
python -B scripts/run_workflow.py --workflow-mode live --print-state --pr-url "https://github.com/abhishek-rahul/sample-payment-service/pull/3"
```

Expected:

```text
business_logic_change
risk high
finding: expired coupon check removed
finding guardrail pass
eval pass
score guardrail pass
recommendation fix_before_merge
```

## 11. Manual Live Test - Good Test PR

Command:

```bash
python -B scripts/run_workflow.py --workflow-mode live --print-state --pr-url "https://github.com/abhishek-rahul/sample-payment-service/pull/4"
```

Expected:

```text
test_change
risk low
findings []
finding guardrail pass
eval pass
score guardrail pass
overall_score 100
recommendation merge_ready
```

## 12. How To Check Fallback

Check:

```json
"errors": []
```

If errors empty, fallback usually did not happen.

Eval fallback sign:

```text
Rule-based eval completed...
```

RAG fallback/failure sign:

```json
"errors": [
  {
    "step_id": "S6A.6",
    "agent_id": "rag_retriever_node"
  }
]
```

## 13. How To Check Retry

Check:

```json
"retry_count": {
  "context_quality": 0,
  "finding_guardrail": 0,
  "eval_judge": 0,
  "scoring": 0
}
```

Any non-zero value means retry happened.

Examples:

```text
finding_guardrail: 2 -> finding guardrail failed twice, PR review reran twice
eval_judge: 1 -> eval failed once, PR review reran once
scoring: 1 -> score guardrail failed once, scoring reran once
```

## 14. How To Check Guardrails

Finding guardrail:

```json
"finding_guardrail_result": {
  "passed": true,
  "issues": []
}
```

Score guardrail:

```json
"score_guardrail_result": {
  "passed": true,
  "issues": []
}
```

Old compatibility guardrail:

```json
"guardrail_result": {
  "pr_scope_passed": true,
  "evidence_passed": true,
  "hallucination_passed": true,
  "score_passed": true
}
```

## 15. How To Check Evals

Eval:

```json
"eval_result": {
  "score": 85,
  "passed": true,
  "reason": "...",
  "checks": [...]
}
```

If `passed=false`, eval retry should happen unless retry count already maxed.

## 16. Troubleshooting

### OpenAI missing

For manual live:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

Run workflow in same shell.

### GitHub rate limit

Public repo can work without token, but token helps avoid rate limits.

### RAG context empty

Check:

```text
Elasticsearch running?
repo indexed?
repo_name and branch correct?
```

### Full pytest temp permission issue

If only temp permission errors happen, use focused suite for Step 6C/6D verification.
