# Step 6A Testing Guide

## Goal

Is guide ka goal hai Step 6A ko confidently test karna:

- Skeleton mode abhi bhi safe hai ya nahi.
- Live mode mocked tests me correctly chal raha hai ya nahi.
- New sample PR usecases cover ho rahe hain ya nahi.
- Final response JSON-serializable hai ya nahi.
- Trace order expected hai ya nahi.

Plain pytest offline-safe rehna chahiye. Matlab tests real GitHub, OpenAI, Elasticsearch, PostgreSQL, Docker, network call nahi karenge.

## Prerequisites

Backend folder me jao:

```bash
cd /c/gitcode/ai_agents/develop/agentic-pr-review-orchestrator/backend
```

Windows PowerShell path:

```powershell
cd C:\gitcode\ai_agents\develop\agentic-pr-review-orchestrator\backend
```

Virtual environment active honi chahiye:

```bash
source .venv/Scripts/activate
```

Ya Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Fast Focused Test Command

Ye command Step 5 skeleton + Step 6A workflow tests run karta hai:

```bash
python -B -m pytest -p no:cacheprovider tests/test_workflow.py tests/test_workflow_skeleton.py tests/test_workflow_live_basic.py
```

Expected:

```text
11 passed
```

Meaning:

- Old workflow node test passed.
- Step 5 skeleton tests passed.
- Step 6A live mocked tests passed.
- New business-logic-without-tests test passed.
- New good-test-only PR test passed.

## Full Test Command

Try:

```bash
python -m pytest --basetemp ./tmp/pytest-agentic-pr
```

If parent folder missing ho, pehle:

```bash
mkdir -p ./tmp
python -m pytest --basetemp ./tmp/pytest-agentic-pr
```

Expected ideal result:

```text
27 passed
```

If Windows permission issue aaye around temp folder, example:

```text
PermissionError: [WinError 5]
FileNotFoundError: ... tmp/pytest-agentic-pr
```

To ye code failure nahi hota. Ye pytest temp folder environment issue hota hai. Focused workflow command still reliable evidence hai.

## Test File Overview

Main test file:

```text
backend/tests/test_workflow_live_basic.py
```

Important constants:

```python
EXPECTED_TRACE = [
    ("S6A.1", "parse_pr_url_node"),
    ("S6A.2", "fetch_pr_data_node"),
    ("S6A.3", "diff_understanding_agent"),
    ("S6A.4", "risk_classification_agent"),
    ("S6A.5", "rag_query_planner_agent"),
    ("S6A.6", "rag_retriever_node"),
    ("S6A.7", "context_quality_agent"),
    ("S6A.8", "pr_review_agent"),
    ("S6A.9", "finding_guardrail_node"),
    ("S6A.10", "eval_judge_agent"),
    ("S6A.11", "final_scoring_agent"),
    ("S6A.12", "response_builder_node"),
]
```

Ye prove karta hai ki live workflow full graph run kar raha hai.

## What Each Test Checks

### 1. Live Workflow Uses Mocked GitHub And LLM

Test:

```text
test_live_workflow_uses_mocked_github_and_llm
```

Checks:

- Real GitHub call nahi hoti.
- Real OpenAI call nahi hoti.
- Mocked high-risk finding final response me aata hai.
- Recommendation `fix_before_merge` hoti hai.

Expected:

```text
final_response.request_id == req_live_test
recommendation == fix_before_merge
first finding severity == high
```

### 2. Final Response Shape And Trace

Test:

```text
test_live_workflow_final_response_shape_and_trace
```

Checks:

- Final response JSON serializable hai.
- Required keys present hain.
- Trace order exactly `EXPECTED_TRACE` hai.
- Final response ke trace me bhi `S6A.12` included hai.

Expected final response keys:

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

### 3. Missing Workflow Mode Behaves As Live

Test:

```text
test_missing_workflow_mode_behaves_as_live
```

Checks:

- Agar state me `workflow_mode` missing hai, nodes live mode use karte hain.

Expected:

```text
first trace == ("S6A.1", "parse_pr_url_node")
recommendation == merge_ready
```

### 4. Docs Only Has No Findings

Test:

```text
test_docs_only_has_no_findings_and_high_score
```

Checks:

- Docs-only PR clean hai.
- Findings empty.
- Score high.
- Recommendation merge_ready.

Expected:

```text
findings == []
overall_score >= 85
recommendation == merge_ready
```

### 5. Validation Removal Gets High Risk

Test:

```text
test_validation_removal_gets_high_risk
```

Checks:

- Validation removal high risk hai.
- Recommendation fix_before_merge hai.

Expected:

```text
risk_level == high
recommendation == fix_before_merge
```

### 6. Business Logic Without Tests Gets Missing Test Finding

Test:

```text
test_business_logic_without_tests_gets_missing_test_finding
```

Setup:

- One source file changed:

```text
app/payment_service.py
```

- No test file changed.
- Review LLM intentionally fail karaya jata hai.
- Fallback findings should run.

Expected:

```text
trace order == EXPECTED_TRACE
recommendation in {"merge_with_caution", "fix_before_merge"}
at least one finding:
  relation_to_pr == missing_test_for_changed_logic
  severity == medium
  file_path == app/payment_service.py
errors contains:
  step_id == S6A.8
  agent_id == pr_review_agent
```

Why important:

Ye prove karta hai ki agar LLM review fail ho, system completely break nahi hota. Basic deterministic fallback still useful finding deta hai.

### 7. Good Test-Only PR Has No Findings And High Score

Test:

```text
test_good_test_only_pr_has_no_findings_and_high_score
```

Setup:

- One test file changed:

```text
tests/test_discount_policy.py
```

- LLM returns:

```text
DiffSummary: test_change
RiskSummary: low
FindingList: []
```

Expected:

```text
trace order == EXPECTED_TRACE
findings == []
risk_level == low
overall_score >= 85
recommendation == merge_ready
errors == []
```

Why important:

Ye prove karta hai ki good test-only PR par system unnecessary issue create nahi karta.

## Manual Skeleton Runner Test

Command:

```bash
python -B scripts/run_workflow.py --pr-url "https://github.com/abhishek-rahul/sample-payment-service/pull/1" --pr-goal "optional goal"
```

Default mode skeleton hai.

Expected trace:

```text
S5.1
S5.2
S5.3
S5.4
S5.5
S5.6
S5.7
S5.8
S5.9
S5.10
S5.11
S5.12
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

## Manual Live Runner Test

Only run if:

- GitHub network available hai.
- OpenAI key shell environment me set hai.

Git Bash:

```bash
export OPENAI_API_KEY="sk-..."
python -B scripts/run_workflow.py \
  --workflow-mode live \
  --pr-url "https://github.com/abhishek-rahul/sample-payment-service/pull/1"
```

Expected:

- Trace `S6A.1` se `S6A.12`.
- Final response JSON.
- Findings may be empty or non-empty depending PR.
- RAG skipped.
- No DB save.

## Common Issues

### OpenAI Missing Credentials

Reason:

Live runner real LLM Gateway use karta hai. `.env` auto-load nahi ho sakta depending config.

Fix:

```bash
export OPENAI_API_KEY="sk-..."
```

### Pytest Temp Permission Error

Reason:

Windows temp folder permission issue.

Try:

```bash
mkdir -p ./tmp
python -m pytest --basetemp ./tmp/pytest-agentic-pr
```

If still fails, run focused suite:

```bash
python -B -m pytest -p no:cacheprovider tests/test_workflow.py tests/test_workflow_skeleton.py tests/test_workflow_live_basic.py
```

### Real GitHub Not Called In Tests

Plain pytest me GitHub mocked hai. Real GitHub sirf manual live runner me call hoga.

## Final Acceptance Checklist

```text
Focused workflow tests: 11 passed
Skeleton mode still S5.x
Live mode S6A.x
Business logic without tests finding exists
Good test-only PR clean
Final responses JSON serializable
No dependency changes
No FastAPI/UI/DB/RAG wiring changes
```
