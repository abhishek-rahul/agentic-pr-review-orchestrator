# Step 3 Testing Guide

## Goal

Is testing ka goal hai verify karna ki Step 3 ke repo indexing building blocks sahi kaam kar rahe hain.

Plain pytest me sirf safe offline tests run hote hain:

```text
file loader tests
text splitter tests
existing backend tests
```

Plain pytest OpenAI ya Elasticsearch ko call nahi karta.

## Part 1: Backend tests run karna

### Step 1: Backend folder me jao

```bash
cd backend
```

Ye zaroori hai because pytest config backend ke andar hai.

### Step 2: Tests run karo

```bash
python -m pytest
```

Expected result:

```text
17 passed
```

Ye prove karta hai:

```text
GitHub PR URL parser still works
guardrails still work
scoring still works
existing workflow placeholder still works
Step 3 loader and splitter work
```

Note:

Agar `.pytest_cache` permission warning aaye, wo main test failure nahi hai. Important line ye hai:

```text
17 passed
```

## Part 2: File loader tests kya verify karte hain

Test file:

```text
backend/tests/test_rag_indexing.py
```

### Test: valid text files include hote hain

Valid files:

```text
app/service.py
README.md
pyproject.toml
config.yaml
```

Ye test prove karta hai ki loader useful text files ko read karta hai.

### Test: secrets and generated folders skip hote hain

Skipped examples:

```text
.env
node_modules/
.git/
.venv/
__pycache__/
binary file with NUL bytes
```

Ye test prove karta hai ki secrets aur generated files Elasticsearch me index nahi honge.

## Part 3: Text splitter tests kya verify karte hain

### Test: chunk_id stable hai

Example:

```text
app/service.py:0
app/service.py:1
app/service.py:2
```

Ye prove karta hai ki chunk IDs predictable hain.

### Test: chunk_index sequential hai

Expected:

```text
0, 1, 2, 3
```

Ye future debugging aur Elasticsearch document tracking me help karega.

### Test: overlap kaam karta hai

Large text ko multiple chunks me split kiya jata hai.

Overlap ka expected behavior:

```text
chunk 0 ke last 10 chars == chunk 1 ke first 10 chars
```

Ye prove karta hai ki context chunk boundary pe abruptly break nahi hota.

### Test: empty content skip hota hai

Input:

```text
""
"   \n\t"
```

Expected:

```text
[]
```

Ye prove karta hai ki useless blank chunks create nahi hote.

### Test: invalid settings fail hoti hain

Invalid examples:

```text
chunk_size = 0
overlap = -1
overlap = chunk_size
overlap > chunk_size
```

Expected:

```text
ValueError
```

Ye prove karta hai ki splitter bad settings silently accept nahi karta.

## Part 4: Static checks

### Check 1: RAG code direct OpenAIEmbeddings use nahi karta

Repo root se run karo:

```bash
rg "OpenAIEmbeddings" backend/app/rag
```

Expected:

```text
No output
```

Meaning:

RAG code embedding gateway use kar raha hai, direct OpenAI class nahi.

### Check 2: Workflow placeholder still unchanged hai

Repo root se run karo:

```bash
rg "retrieve_context_placeholder" backend/app/graph/nodes.py backend/app/rag/retriever.py
```

Expected:

```text
backend/app/rag/retriever.py:def retrieve_context_placeholder(query: str) -> list[str]:
backend/app/graph/nodes.py:from app.rag.retriever import retrieve_context_placeholder
backend/app/graph/nodes.py:        for raw_context in retrieve_context_placeholder(item.query):
```

Meaning:

Current LangGraph workflow abhi bhi placeholder retrieval use kar raha hai. Real retrieval ready hai, but wired later hoga.

### Check 3: Dependency file unchanged

Repo root se run karo:

```bash
git diff -- backend/pyproject.toml
```

Expected:

```text
No output
```

Meaning:

Step 3 me dependency versions change nahi hui.

## Part 5: Manual indexing test

Ye test plain pytest ka part nahi hai because ye OpenAI embeddings aur Elasticsearch dono use karega.

Prerequisites:

```text
OPENAI_API_KEY set ho
Elasticsearch running ho
Sample repo available ho
```

### Step 1: Backend folder me jao

```bash
cd backend
```

### Step 2: Elasticsearch start karo

Repo root se Docker Compose run hota hai:

```bash
docker compose up -d elasticsearch
```

### Step 3: Backend env check karo

`backend/.env` me ye values honi chahiye:

```text
OPENAI_API_KEY=...
ELASTICSEARCH_URL=http://localhost:9200
```

### Step 4: Indexing command run karo

Backend folder se:

```bash
python scripts/index_repo.py --repo-path ../sample-payment-service --repo-name sample-payment-service --branch main
```

Expected output:

```text
Indexed <count> chunks for repo sample-payment-service on branch main
```

Meaning:

Files load hue, chunks bane, embeddings generate hue, aur Elasticsearch me documents save hue.

## Part 6: Common issues

### Issue: ModuleNotFoundError for elasticsearch

Meaning:

Active Python environment me project dependencies installed nahi hain.

Fix:

Backend environment activate/install karo as per project setup.

### Issue: OpenAI API key error

Meaning:

Manual indexing command embeddings banata hai, so API key required hai.

Fix:

`backend/.env` me `OPENAI_API_KEY` set karo, ya same shell me environment variable set karo.

### Issue: Elasticsearch connection error

Meaning:

Elasticsearch running nahi hai ya URL wrong hai.

Fix:

```bash
docker compose up -d elasticsearch
```

Then check:

```bash
curl http://localhost:9200
```

## Final acceptance checklist

```text
python -m pytest passes
backend/pyproject.toml unchanged
backend/app/rag has no direct OpenAIEmbeddings
.env and generated folders are skipped
splitter creates chunk_id and chunk_index
workflow still uses retrieve_context_placeholder
manual indexing command available for Elasticsearch indexing
```
