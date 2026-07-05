# Step 6B Understanding - RAG Integration With Live PR Review

## Goal

Step 6B ka goal hai existing Step 6A live PR review me RAG ko actually use karna.

Simple terms me:

1. PR ka URL parse hota hai.
2. GitHub se PR metadata aur changed files fetch hoti hain.
3. AI diff samajhta hai.
4. AI risk classify karta hai.
5. AI RAG queries banata hai.
6. Retriever Elasticsearch/indexed repo se related context nikalta hai.
7. Context quality check hota hai.
8. PR review agent diff + retrieved context dekhkar findings banata hai.
9. Guardrails, eval, scoring, final response run hote hain.

Step 6B me RAG active hua hai, lekin final response ka shape same rakha gaya hai. Isliye Step 6A ke consumer ko response parse karne me koi breaking change nahi aata.

## What Changed

### 1. RAG Planning Active Hua

File:

```text
backend/app/graph/nodes.py
```

Function:

```python
rag_query_planner_agent(state)
```

Step 6A me live mode me ye mostly skip tha. Step 6B me ye LLM Gateway ke through `RAGQueryPlan` banata hai.

Example output:

```json
{
  "queries": [
    {
      "query": "payment service related tests",
      "purpose": "Find related tests"
    }
  ],
  "top_k": 6
}
```

Iska kaam hai PR ke hisaab se focused search queries banana.

Broad/generic queries jaise `best practices`, `clean code`, `general review` filter ho jaati hain.

## 2. RAG Retrieval Active Hua

Function:

```python
rag_retriever_node(state)
```

Ye existing retriever ko call karta hai:

```python
retrieve_context(query, repo_name, branch, top_k)
```

Important:

- `retrieve_context(...)` ka signature change nahi hua.
- `retrieve_context_placeholder(...)` unchanged hai.
- Graph nodes direct Elasticsearch ya embeddings instantiate nahi karte.
- Retriever failure aaye to workflow crash nahi hota; error record hota hai aur context empty ho jata hai.

Retrieved context `state["retrieved_context"]` me save hota hai.

## 3. Context Quality Check Active Hua

Function:

```python
context_quality_agent(state)
```

Ye pehle `_basic_context_check(state)` chalata hai.

Phir LLM Gateway se `ContextQualityResult` lene ki koshish karta hai.

If LLM fail ho jaye:

```text
fallback -> _basic_context_check(state)
```

Meaning:

- Docs/test-only PR empty context ke saath bhi pass ho sakta hai.
- Business logic PR me context nahi mila to context quality fail ho sakti hai.
- Fail hone par router RAG query planner par retry kara sakta hai.

## 4. Retry Router Active Hua

File:

```text
backend/app/graph/routers.py
```

Function:

```python
route_after_context_quality(state)
```

Simple rule:

```text
if context enough:
    go to pr_review
else if context_quality retry count < 3:
    increment retry_count["context_quality"]
    go back to rag_query_planner
else:
    go to pr_review anyway
```

Important:

- Retry count sirf router me increment hota hai.
- Nodes retry count increment nahi karte.
- Max retry 3 hai.

## 5. PR Review Prompt Me Context Add Hua

Function:

```python
_review_prompt(state)
```

Ab prompt me ye include hota hai:

- PR metadata
- changed files
- diff summary
- risk summary
- context quality
- retrieved context
- raw diff

But ek important guard instruction bhi hai:

```text
Retrieved context sirf support ke liye hai.
Context files se issue tabhi report karna hai jab current PR ne issue introduce, modify, ya worse kiya ho.
```

Isse AI old repo context ko galat finding ke roop me report karne se bachta hai.

## Important Modes

### Skeleton Mode

`workflow_mode="skeleton"` unchanged hai:

- no GitHub
- no OpenAI
- no Elasticsearch
- no PostgreSQL
- trace `S5.1` to `S5.12`
- deterministic dummy final response

## Live Mode

`workflow_mode="live"` me:

- GitHub fetch hota hai
- LLM structured output use hota hai
- RAG query planning hoti hai
- real retriever call hota hai
- context quality check hota hai
- final response Step 6A shape me hi aata hai

Trace IDs abhi bhi `S6A.1` to `S6A.12` hain. Naam Step 6A isliye rakha gaya hai taaki existing compatibility break na ho.

## State Fields Added/Used

File:

```text
backend/app/graph/state.py
```

Important fields:

```python
rag_query_plan
previous_rag_queries
retrieved_context
context_quality
retry_count
errors
trace
```

`previous_rag_queries` ka use retry ke time repeated query avoid karne ke liye hota hai.

## Example From Real Run

PR:

```text
Business logic change without tests
```

Change:

```text
processing_fee add hua payment_service.py me
```

Workflow ne detect kiya:

```text
main_change_type = business_logic_change
risk = medium
RAG queries = 5
retrieved context chunks = 7
finding = missing test for changed payment logic
recommendation = fix_before_merge
score = 57
```

Ye expected behavior hai. Business logic change financial calculation me hua aur tests update nahi hue, isliye finding aayi.

## What Is Not Changed

Step 6B me ye cheeze intentionally nahi badli:

- dependency versions
- `backend/pyproject.toml`
- FastAPI routes
- UI
- DB models
- Alembic
- RAG indexer
- `retrieve_context(...)` signature
- `retrieve_context_placeholder(...)`
- final response shape
- workflow trace order
- Step 5 skeleton behavior

## Mental Model

Step 6B ko aise samjho:

```text
Step 6A = PR review AI ko diff dikha ke basic answer
Step 6B = PR review AI ko diff ke saath repo context bhi dikha ke better answer
```

RAG yahan decision maker nahi hai. RAG sirf extra reference/context deta hai. Final finding current PR diff se tied honi chahiye.
