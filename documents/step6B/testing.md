# Step 6B Testing Guide

## Goal

Is guide ka goal hai Step 6B ko simple way me test karna.

Hum ye prove karna chahte hain:

- Step 5 skeleton abhi bhi safe hai.
- Step 6A final response shape abhi bhi same hai.
- Step 6B me RAG planning, retrieval, context quality active hai.
- Unit tests real GitHub, OpenAI, Elasticsearch, Docker, PostgreSQL ko touch nahi karte.
- Manual live run me RAG context retrieve ho sakta hai if repo indexed hai.

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

## 3. Focused Workflow Tests Chalao

Command:

```bash
python -B -m pytest -p no:cacheprovider tests/test_workflow.py tests/test_workflow_skeleton.py tests/test_workflow_live_basic.py
```

Expected:

```text
20 passed
```

Ye kya test karta hai:

- old workflow basic test pass hai
- Step 5 skeleton pass hai
- Step 6A live mocked tests pass hain
- Step 6B RAG planner tests pass hain
- Step 6B retriever tests pass hain
- Step 6B context-quality tests pass hain
- retry router tests pass hain

## 4. Full Pytest Try Karo

Command:

```bash
python -B -m pytest -p no:cacheprovider --basetemp ./tmp/pytest-agentic-pr
```

Expected ideal:

```text
36 passed
```

But Windows me kabhi-kabhi temp folder permission issue aa sakta hai:

```text
PermissionError: [WinError 5]
```

If aisa aaye aur focused workflow tests pass hain, to Step 6B logic ka issue nahi hai. Ye local temp/cache permission issue hota hai.

## 5. Compile Check

Normal compile command:

```bash
python -B -m compileall app
```

If pycache permission issue aaye:

```text
PermissionError: __pycache__
```

PowerShell me pycache ko writable temp location par redirect karke run karo:

```powershell
$env:PYTHONPYCACHEPREFIX="C:\tmp\agentic-pr-pycache"
python -B -m compileall app
```

Expected:

```text
compileall complete without syntax error
```

## 6. Manual Skeleton Run

Command:

```bash
python -B scripts/run_workflow.py --workflow-mode skeleton --pr-url "https://github.com/abhishek-rahul/sample-payment-service/pull/1"
```

Expected:

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

Ye prove karta hai:

- Step 5 skeleton untouched hai.
- No GitHub/OpenAI/Elasticsearch needed.

## 7. Manual Live Run Without Printing Full State

Prerequisites:

- public GitHub PR accessible ho
- `OPENAI_API_KEY` same shell me set ho
- if RAG context chahiye, repo pehle indexed ho
- Elasticsearch running ho if real RAG retrieval test karna hai

Command:

```bash
python -B scripts/run_workflow.py --workflow-mode live --pr-url "https://github.com/abhishek-rahul/sample-payment-service/pull/2"
```

Expected trace:

```text
S6A.1 parse_pr_url_node passed
S6A.2 fetch_pr_data_node passed
S6A.3 diff_understanding_agent passed
S6A.4 risk_classification_agent passed
S6A.5 rag_query_planner_agent passed
S6A.6 rag_retriever_node passed
S6A.7 context_quality_agent passed
S6A.8 pr_review_agent passed
S6A.9 finding_guardrail_node passed
S6A.10 eval_judge_agent passed
S6A.11 final_scoring_agent passed
S6A.12 response_builder_node passed
```

Ye prove karta hai:

- saare agents/nodes run hue
- RAG planning active hai
- retrieval active hai
- context quality active hai
- final response build hua

## 8. Manual Live Run With Full State

If `--print-state` available hai:

```bash
python -B scripts/run_workflow.py --workflow-mode live --print-state --pr-url "https://github.com/abhishek-rahul/sample-payment-service/pull/2"
```

Full state me check karo:

```text
rag_query_plan.queries
previous_rag_queries
retrieved_context
context_quality
findings
score_result
final_response
trace
errors
```

Expected:

- `rag_query_plan.queries` empty nahi honi chahiye for business logic PR
- `retrieved_context` me repo chunks aa sakte hain if index available hai
- `context_quality.context_enough = true` if context mila
- `errors = []` ideal case me

## 9. Manual PR #2 Expected Behavior

Example PR:

```text
https://github.com/abhishek-rahul/sample-payment-service/pull/2
```

Expected high-level output:

```text
business_logic_change detect hoga
risk medium ya high ho sakta hai
RAG queries banengi
payment docs/tests/source context retrieve ho sakta hai
finding: processing_fee business logic changed without matching tests
recommendation: fix_before_merge
```

## 10. What Each Important Test Means

### `test_rag_query_planner_returns_structured_plan`

Proof:

```text
LLM se structured RAGQueryPlan aa raha hai aur state me save ho raha hai.
```

### `test_rag_query_planner_fallback_filters_generic_queries`

Proof:

```text
LLM fail hone par deterministic fallback query plan banta hai.
Generic queries remove hoti hain.
```

### `test_rag_retriever_uses_mocked_retrieve_context_and_dedupes`

Proof:

```text
retriever call hota hai, duplicate context chunks remove hote hain.
```

### `test_rag_retriever_handles_failure_gracefully`

Proof:

```text
Elasticsearch/retriever fail ho to workflow crash nahi hota.
Error record hota hai.
```

### `test_context_quality_passes_for_test_only_empty_context`

Proof:

```text
Test-only PR ke liye empty context acceptable hai.
```

### `test_context_quality_fails_for_business_logic_empty_context`

Proof:

```text
Business logic PR me context missing ho to system more context maangta hai.
```

### `test_context_router_retries_and_increments_only_in_router`

Proof:

```text
Context retry counter sirf router increment karta hai.
```

### `test_context_router_proceeds_after_max_retry`

Proof:

```text
3 retries ke baad workflow stuck nahi hota, PR review par proceed karta hai.
```

## Troubleshooting

### Problem: OpenAI missing

In unit tests ye problem nahi aani chahiye because LLM mocked hai.

Manual live run ke liye:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

Same shell me command run karo.

### Problem: Elasticsearch unavailable

Unit tests me issue nahi aana chahiye because retriever mocked hai.

Manual live RAG ke liye Elasticsearch running + repo indexed hona chahiye.

### Problem: RAG retrieved_context empty hai

Possible reasons:

- repo indexed nahi hai
- wrong repo_name/branch
- Elasticsearch running nahi hai
- queries relevant nahi bani

Workflow phir bhi crash nahi karega.

### Problem: Full pytest temp permission error

Ye code issue nahi hota usually. Focused workflow tests run karke Step 6B verify kar sakte ho.
