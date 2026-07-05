# Step 6B Function Call Flow - Only New/Changed RAG Flow

## Scope

Ye doc sirf Step 6B me jo changes hue unka function call flow explain karta hai.

Is doc me full workflow repeat nahi hai. Step 6B ka main change ye hai:

```text
S6A.5 rag_query_planner_agent
S6A.6 rag_retriever_node
S6A.7 context_quality_agent
route_after_context_quality
pr_review_agent prompt me retrieved_context add
```

Step 6A ke baaki nodes same hain.

## Step 6B Change Ka High-Level Flow

```text
risk_classification_agent complete hota hai
-> rag_query_planner_agent
-> rag_retriever_node
-> context_quality_agent
-> route_after_context_quality
   -> if context weak and retry < 3:
      -> rag_query_planner_agent again
   -> else:
      -> pr_review_agent
```

Simple words me:

```text
Risk samajhne ke baad system repo context search karta hai.
Context mila ya nahi, ye check hota hai.
Agar context weak hai to max 3 baar better query banake retry hota hai.
Fir PR review agent diff + context dekh ke finding banata hai.
```

## Changed State Fields

File:

```text
backend/app/graph/state.py
```

Step 6B me main extra state field:

```python
previous_rag_queries: list[str]
```

Purpose:

```text
Retry ke time same RAG query baar-baar repeat na ho.
```

Step 6B me actively used fields:

```python
state["rag_query_plan"]
state["previous_rag_queries"]
state["retrieved_context"]
state["context_quality"]
state["retry_count"]["context_quality"]
```

## 1. rag_query_planner_agent

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
rag_query_planner_agent(state)
```

### Purpose

PR ke current diff/risk ke basis par RAG search queries banana.

Example:

```text
payment service related source code
payment service related tests
payment validation rules
```

### Function Call Flow

```text
rag_query_planner_agent(state)
-> _workflow_mode(state)
-> if live:
     _rag_query_prompt(state)
     -> _get_structured_llm(RAGQueryPlan)
     -> llm.invoke(prompt)
     -> _clean_rag_query_plan(plan, state)
     -> update state["rag_query_plan"]
     -> update state["previous_rag_queries"]
     -> add_trace(S6A.5)
```

### If LLM Fails

```text
rag_query_planner_agent(state)
-> LLM call fails
-> _append_error(state, "S6A.5", "rag_query_planner_agent", error)
-> _fallback_rag_query_plan(state)
-> _clean_rag_query_plan(plan, state)
-> state["rag_query_plan"]
```

Meaning:

```text
LLM fail hone par bhi workflow rukta nahi.
System deterministic fallback queries banata hai.
```

### Helper: _rag_query_prompt

Function:

```python
_rag_query_prompt(state)
```

Prompt me ye data jata hai:

```text
PR goal
changed files
diff summary
risk summary
previous RAG queries
missing context
suggested queries
```

Purpose:

```text
LLM ko focused repo-search queries banane ke liye enough information dena.
```

### Helper: _clean_rag_query_plan

Function:

```python
_clean_rag_query_plan(plan, state)
```

Ye clean karta hai:

```text
empty query remove
already-used query remove
generic query remove
max 5 queries keep
top_k ko 1 se 10 ke range me clamp
```

Generic query example:

```text
best practices
clean code
security tips
general review
how to write good tests
```

## 2. rag_retriever_node

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
rag_retriever_node(state)
```

### Purpose

`rag_query_plan` ki queries execute karke repo context chunks nikalna.

### Function Call Flow

```text
rag_retriever_node(state)
-> plan = state["rag_query_plan"]
-> for each query in plan.queries:
     rag_retriever.retrieve_context(
         query,
         repo_name=state["repo"],
         branch=state["pr_metadata"].base_branch,
         top_k=plan.top_k
     )
-> _dedupe_and_filter_contexts(contexts)
-> state["retrieved_context"]
-> add_trace(S6A.6)
```

### Real Retriever Call

Actual function:

```python
retrieve_context(query, repo_name, branch, top_k)
```

File:

```text
backend/app/rag/retriever.py
```

Important:

```text
Step 6B ne retriever rewrite nahi kiya.
Existing retrieve_context(...) ko reuse kiya.
retrieve_context_placeholder(...) unchanged hai.
```

### If No Queries

```text
if no rag_query_plan or no queries:
    state["retrieved_context"] = []
    trace S6A.6 skipped
```

### If Retriever Fails

```text
retrieve_context throws error
-> _append_error(state, "S6A.6", "rag_retriever_node", error)
-> state["retrieved_context"] = []
-> workflow continues
```

Meaning:

```text
Elasticsearch down ho to bhi workflow crash nahi karega.
Review weak context ke saath continue kar sakta hai.
```

### Helper: _dedupe_and_filter_contexts

Function:

```python
_dedupe_and_filter_contexts(contexts)
```

Purpose:

```text
Duplicate chunks remove karna.
Unsafe files remove karna.
```

Unsafe examples:

```text
.env
.git/
.venv/
node_modules/
dist/
build/
__pycache__/
*.log
*.pyc
*.jar
images
```

## 3. context_quality_agent

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
context_quality_agent(state)
```

### Purpose

Retrieved context enough hai ya nahi, ye decide karna.

### Function Call Flow

```text
context_quality_agent(state)
-> _basic_context_check(state)
-> _context_quality_prompt(state, basic_result)
-> _get_structured_llm(ContextQualityResult)
-> llm.invoke(prompt)
-> state["context_quality"]
-> add_trace(S6A.7)
```

### If Context Quality LLM Fails

```text
LLM call fails
-> _append_error(state, "S6A.7", "context_quality_agent", error)
-> state["context_quality"] = _basic_context_check(state)
```

Meaning:

```text
Context quality LLM fail hone par deterministic basic check use hota hai.
```

### Helper: _basic_context_check

Function:

```python
_basic_context_check(state)
```

Rules:

```text
docs/test-only PR:
    empty context bhi okay

retrieved_context exists:
    context enough

business_logic_change and no context:
    context not enough
    suggested source/test queries

other changes:
    context acceptable
```

Example business logic no context:

```json
{
  "context_enough": false,
  "reason": "No context retrieved for business logic PR.",
  "missing_context": ["related source code", "related tests"],
  "suggested_queries": ["payment related source code", "payment related tests"]
}
```

### Helper: _context_quality_prompt

Function:

```python
_context_quality_prompt(state, basic_result)
```

Prompt me ye data jata hai:

```text
basic check result
PR goal
changed files
diff summary
risk summary
RAG query plan
retrieved context preview
```

Purpose:

```text
LLM ko batana ki retrieved context review ke liye enough hai ya nahi.
```

## 4. route_after_context_quality

File:

```text
backend/app/graph/routers.py
```

Function:

```python
route_after_context_quality(state)
```

### Purpose

Context quality ke baad decide karna:

```text
PR review pe jana hai
ya RAG query planner ko retry karna hai
```

### Function Call Flow

```text
route_after_context_quality(state)
-> if workflow_mode == "skeleton":
      return "pr_review"

-> if state["context_quality"].context_enough:
      return "pr_review"

-> current_retry = state["retry_count"]["context_quality"]

-> if current_retry < 3:
      state["retry_count"]["context_quality"] += 1
      return "rag_query_planner"

-> return "pr_review"
```

Important:

```text
retry count sirf router increment karta hai.
nodes retry count increment nahi karte.
```

## 5. workflow.py Edge Change

File:

```text
backend/app/graph/workflow.py
```

Old flow:

```text
context_quality -> pr_review
```

Step 6B flow:

```text
context_quality
-> route_after_context_quality
   -> rag_query_planner
   -> pr_review
```

Code concept:

```python
graph.add_conditional_edges(
    "context_quality",
    route_after_context_quality,
    {
        "rag_query_planner": "rag_query_planner",
        "pr_review": "pr_review",
    },
)
```

Meaning:

```text
Agar context weak hai to graph loop karke RAG query planner par ja sakta hai.
Max retry ke baad PR review par proceed karta hai.
```

## 6. pr_review_agent Prompt Change

File:

```text
backend/app/graph/nodes.py
```

Changed helper:

```python
_review_prompt(state)
```

Step 6B me prompt me add hua:

```text
Context quality
Retrieved context
```

Flow:

```text
pr_review_agent(state)
-> _review_prompt(state)
   -> includes state["context_quality"]
   -> includes state["retrieved_context"]
-> _get_structured_llm(FindingList)
-> llm.invoke(prompt)
```

Important prompt rule:

```text
Retrieved repo context supporting information hai.
Finding tabhi report karo jab current PR ne issue introduce, modify, ya worse kiya ho.
```

Meaning:

```text
AI old repo files dekh kar random issue report nahi karega.
Finding current PR diff se linked honi chahiye.
```

## 7. Test Helper Cleanup

File:

```text
backend/tests/test_workflow_live_basic.py
```

Changed helper:

```python
_run_with_docs_only()
```

Step 6B cleanup:

```text
nodes.rag_retriever.retrieve_context monkeypatch hota hai
return []
finally me original restore hota hai
```

Purpose:

```text
Docs-only unit test accidentally real Elasticsearch ko touch na kare.
```

## End-to-End Step 6B Changed Flow

Only changed/new part:

```text
risk_classification_agent
-> rag_query_planner_agent
   -> _rag_query_prompt
   -> _get_structured_llm(RAGQueryPlan)
   -> _clean_rag_query_plan
   -> state["rag_query_plan"]
   -> state["previous_rag_queries"]

-> rag_retriever_node
   -> retrieve_context(query, repo_name, branch, top_k)
   -> _dedupe_and_filter_contexts
   -> state["retrieved_context"]

-> context_quality_agent
   -> _basic_context_check
   -> _get_structured_llm(ContextQualityResult)
   -> state["context_quality"]

-> route_after_context_quality
   -> if weak context and retry < 3:
        back to rag_query_planner_agent
      else:
        pr_review_agent

-> pr_review_agent
   -> _review_prompt includes retrieved_context
   -> findings must remain tied to current PR
```

## What Did Not Change

Step 6B did not change:

```text
parse_pr_url_node
fetch_pr_data_node
diff_understanding_agent
risk_classification_agent
finding_guardrail_node
eval_judge_agent
final_scoring_agent
response_builder_node
final_response shape
Step 5 skeleton response
retrieve_context(...) signature
retrieve_context_placeholder(...)
```

## One Simple Summary

Step 6B ka function-flow bas itna hai:

```text
Risk ke baad RAG queries banao,
queries se repo context lao,
context enough hai ya nahi check karo,
weak ho to max 3 retry karo,
fir PR review agent ko diff + context ke saath run karo.
```
