# Step 6A Understanding - Basic Live AI PR Review

## Goal

Step 6A ka goal production-perfect PR review banana nahi hai. Iska goal hai first basic live AI review flow chalana:

1. User ek GitHub PR URL deta hai.
2. Workflow PR URL parse karta hai.
3. Live mode me GitHub se PR metadata aur changed files fetch hoti hain.
4. LLM Gateway ke through basic structured AI outputs bante hain.
5. Basic findings, score, recommendation, trace, aur final JSON response milta hai.

Step 5 skeleton mode abhi bhi same hai. Skeleton mode ka kaam hai offline deterministic workflow proof. Live mode ka kaam hai real PR ke upar basic AI review.

## Important Modes

### Skeleton Mode

`workflow_mode="skeleton"` ka matlab:

- GitHub API call nahi hoti.
- OpenAI call nahi hoti.
- Elasticsearch call nahi hoti.
- PostgreSQL call nahi hoti.
- Trace IDs `S5.1` se `S5.12` tak rehte hain.
- Final response fixed dummy response hota hai.

Skeleton final response:

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

### Live Mode

`workflow_mode="live"` ka matlab:

- Real GitHub PR metadata fetch hota hai.
- Real changed files fetch hoti hain.
- LLM Gateway structured output ke through basic AI reasoning hoti hai.
- RAG abhi bhi skip hota hai.
- Eval judge abhi LLM nahi hai.
- Retry loops abhi nahi hain.
- Trace IDs `S6A.1` se `S6A.12` tak rehte hain.

If `workflow_mode` missing ho, nodes usse live treat karte hain. But runner ka default abhi bhi skeleton hai safety ke liye.

## Main Files Changed

### `backend/app/graph/nodes.py`

Yahan Step 6A ka main behavior hai. Har workflow node yahin define hai:

- `parse_pr_url_node`
- `fetch_pr_data_node`
- `diff_understanding_agent`
- `risk_classification_agent`
- `rag_query_planner_agent`
- `rag_retriever_node`
- `context_quality_agent`
- `pr_review_agent`
- `finding_guardrail_node`
- `eval_judge_agent`
- `final_scoring_agent`
- `response_builder_node`

Important helper functions:

- `_workflow_mode(state)`: missing mode ko live treat karta hai.
- `_step_id(state, skeleton_id, live_id)`: skeleton me S5 trace, live me S6A trace choose karta hai.
- `_append_error(...)`: minimal error object add karta hai.
- `_get_structured_llm(schema)`: LLM Gateway use karta hai aur structured output wrapper banata hai.
- `_deterministic_diff_summary(...)`: fallback diff summary banata hai.
- `_deterministic_risk_summary(...)`: fallback risk summary banata hai.
- `_fallback_findings(...)`: fallback findings banata hai.
- `_finding_to_response(...)`: internal Finding object ko UI-friendly final response dict me convert karta hai.

### `backend/scripts/run_workflow.py`

Local runner hai. Isse workflow manually chal sakta hai.

Default:

```bash
python scripts/run_workflow.py --pr-url "https://github.com/owner/repo/pull/1"
```

Default mode skeleton hai.

Live mode:

```bash
python scripts/run_workflow.py --workflow-mode live --pr-url "https://github.com/owner/repo/pull/1"
```

Runner initial state me ye set karta hai:

```python
retry_count = {
    "context_quality": 0,
    "finding_guardrail": 0,
    "eval_judge": 0,
    "scoring": 0,
}
errors = []
trace = []
```

### `backend/tests/test_workflow_live_basic.py`

Yahan Step 6A ke offline-safe tests hain. Ye real GitHub ya OpenAI call nahi karte. Sab mocked hai.

Recently add kiye gaye sample PR tests:

- Business logic change without tests.
- Good test-only PR with proper tests.

## What Each Node Does

### S6A.1 `parse_pr_url_node`

Input:

```text
https://github.com/owner/repo/pull/123
```

Output state me:

- `owner`
- `repo`
- `pr_number`
- `pr_ref`

Trace:

```text
S6A.1 parse_pr_url_node passed PR URL parsed
```

### S6A.2 `fetch_pr_data_node`

Live mode me existing GitHub client use hota hai:

- `fetch_pr_metadata`
- `fetch_changed_files`

State me save hota hai:

- `pr_metadata`
- `changed_files`
- `raw_diff`

If GitHub fetch fail hota hai, error add hota hai:

```json
{
  "step_id": "S6A.2",
  "agent_id": "fetch_pr_data_node",
  "message": "..."
}
```

### S6A.3 `diff_understanding_agent`

LLM Gateway use karke structured `DiffSummary` banata hai.

Prompt me diya jata hai:

- PR title
- PR goal
- changed files
- trimmed raw diff
- allowed enum values

If LLM fail hota hai, deterministic fallback use hota hai.

### S6A.4 `risk_classification_agent`

LLM Gateway use karke structured `RiskSummary` banata hai.

If LLM fail hota hai, deterministic fallback risk summary use hoti hai.

Examples:

- docs only -> low
- test only -> low
- payment/auth/security -> high
- business logic -> medium
- validation removal -> high

### S6A.5 `rag_query_planner_agent`

Step 6A me RAG planning skip hai.

State:

```python
rag_query_plan = RAGQueryPlan(queries=[], top_k=0)
```

### S6A.6 `rag_retriever_node`

Step 6A me real Elasticsearch retrieval skip hai.

State:

```python
retrieved_context = []
```

### S6A.7 `context_quality_agent`

Step 6A me context quality placeholder hai.

State:

```python
context_enough = True
reason = "RAG context quality check skipped in Step 6A."
```

### S6A.8 `pr_review_agent`

LLM Gateway structured `FindingList` output use karta hai.

Rules prompt me explicitly diye gaye:

- Current PR diff only.
- Unrelated legacy issues ignore karo.
- File path invent mat karo.
- Line number invent mat karo.
- Docs-only/test-only usually no findings.
- Business logic without tests can be a finding.
- Removed validation visible in diff should be high risk.

If review LLM fail hota hai, fallback findings use hote hain.

Fallback examples:

- Source file changed but test file nahi changed -> missing test finding.
- Validation removal visible -> high-risk validation finding.

### S6A.9 `finding_guardrail_node`

Basic offline-safe guardrails:

- Finding changed file se related hai ya nahi.
- Evidence present hai ya nahi.
- File path hallucinated to nahi.

No retry loop.

### S6A.10 `eval_judge_agent`

Abhi rule-based eval use hota hai. LLM judge nahi hai.

### S6A.11 `final_scoring_agent`

Basic scoring karta hai:

- Low risk ka base score high.
- Medium risk ka base score medium-high.
- High risk ka base score lower.
- Finding severity ke hisab se penalty.
- Guardrail fail ho to score cap.

Recommendation:

- `merge_ready`
- `merge_with_caution`
- `fix_before_merge`
- `needs_human_review`

### S6A.12 `response_builder_node`

Final JSON response banata hai.

Important: pehle `S6A.12` trace add hota hai, phir trace serialize hota hai. Isliye final response ke trace me `S6A.12` bhi present hota hai.

Live final response shape:

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

## Recent Tests Added

### Business Logic Without Tests

Test name:

```text
test_business_logic_without_tests_gets_missing_test_finding
```

Purpose:

Verify karta hai ki agar source file change ho aur matching test file na ho, to fallback finding generate hota hai.

Expected finding:

```json
{
  "relation_to_pr": "missing_test_for_changed_logic",
  "severity": "medium",
  "file_path": "app/payment_service.py"
}
```

Is test me review LLM intentionally fail karaya gaya hai. Isliye expected error:

```json
{
  "step_id": "S6A.8",
  "agent_id": "pr_review_agent"
}
```

### Good Test-Only PR

Test name:

```text
test_good_test_only_pr_has_no_findings_and_high_score
```

Purpose:

Verify karta hai ki agar sirf test file change hui hai aur LLM findings empty deta hai, to review clean rahe.

Expected:

- findings empty
- risk low
- score >= 85
- recommendation merge_ready
- errors empty

## What We Did Not Implement

Step 6A intentionally basic hai. Ye cheezein abhi nahi ki:

- Real RAG retrieval.
- Elasticsearch context retrieval.
- Retry loops.
- Eval judge LLM.
- PostgreSQL save.
- FastAPI route integration.
- Frontend integration.
- GitHub comment posting.
- Production-level prompt quality.
- Full code review accuracy.

## Simple Mental Model

Socho workflow ek pipeline hai:

```text
PR URL
-> GitHub data
-> AI diff summary
-> AI risk summary
-> skip RAG
-> AI/basic findings
-> basic guardrails
-> basic eval
-> basic scoring
-> final JSON response
```

Skeleton mode same pipeline ka dummy rehearsal hai.

Live mode same pipeline ka real PR data + basic AI version hai.
