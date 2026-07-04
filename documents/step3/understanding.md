# Step 3 Understanding: Repo Context Indexing in Simple Terms

## Step 3 ka goal

Step 3 ka kaam hai local sample repository ko Elasticsearch me searchable context ke form me store karna.

Simple terms me:

```text
Local repo files
  -> safe files load karo
  -> text ko small chunks me tod do
  -> har chunk ka embedding banao
  -> Elasticsearch me save karo
  -> later PR review ke time related context retrieve karo
```

Ye PR review workflow ko future me help karega, kyunki LLM ko pura repo dene ki jagah sirf related files/chunks diye jayenge.

## Is step me kya bana

### 1. Repo file loading

File:

```text
backend/app/rag/file_loader.py
```

Main function:

```python
load_repo_files(repo_path: str) -> list[RepoFile]
```

Ye function repo folder ke andar walk karta hai aur sirf useful text files load karta hai.

Allowed files:

```text
.py, .md, .txt, .toml, .yaml, .yml, .json
```

Skipped folders:

```text
.git, .venv, __pycache__, .pytest_cache, node_modules, dist, build
```

Skipped files:

```text
.env, .pyc, images, zip files, binary files
```

Important point:

`.env` skip hota hai because secrets/API keys index nahi karne hain.

## 2. Text splitting

File:

```text
backend/app/rag/text_splitter.py
```

Main function:

```python
split_repo_file(repo_file: RepoFile, chunk_size: int = 1200, overlap: int = 150) -> list[RepoChunk]
```

Ye ek file ke content ko chhote chunks me todta hai.

Example:

```text
Long file content
  -> chunk 0
  -> chunk 1
  -> chunk 2
```

Overlap ka matlab:

Ek chunk ke last ke kuch characters next chunk ke start me repeat hote hain. Isse context break nahi hota.

Har chunk me ye data hota hai:

```text
file_path
chunk_id
chunk_index
content
```

Example chunk id:

```text
app/service.py:0
app/service.py:1
```

## 3. Embedding + Elasticsearch indexing

File:

```text
backend/app/rag/indexer.py
```

Main function:

```python
index_repo_chunks(repo_name: str, branch: str, chunks: list[RepoChunk]) -> int
```

Ye function:

1. Chunk content leta hai.
2. `get_embeddings()` se embeddings banata hai.
3. Elasticsearch index create karta hai if missing.
4. Chunks ko Elasticsearch me save karta hai.

Index name:

```text
pr-review-repo-context
```

Stored fields:

```text
repo_name
branch
file_path
chunk_id
chunk_index
content
content_vector
```

Important:

RAG code directly `OpenAIEmbeddings` use nahi karta. Ye existing gateway use karta hai:

```python
from app.ai.embedding_gateway import get_embeddings
```

Iska benefit: future me embedding provider change karna easy rahega.

## 4. Real retrieval function

File:

```text
backend/app/rag/retriever.py
```

Functions:

```python
retrieve_context_placeholder(query: str) -> list[str]
retrieve_context(query: str, repo_name: str, branch: str, top_k: int = 6)
```

Placeholder abhi workflow ke liye rakha gaya hai.

Real `retrieve_context(...)` future workflow integration ke liye ready hai.

Ye function:

1. Query ka embedding banata hai.
2. Elasticsearch me same `repo_name` aur `branch` ke chunks search karta hai.
3. Top matching context chunks return karta hai.

Abhi workflow unchanged hai, so current LangGraph flow break nahi hota.

## 5. Repo indexing service

File:

```text
backend/app/rag/repo_index_service.py
```

Main function:

```python
index_local_repo(repo_path: str, repo_name: str, branch: str = "main") -> int
```

Ye high-level function hai:

```text
load files
  -> split files into chunks
  -> index chunks into Elasticsearch
  -> return count
```

## 6. CLI script

File:

```text
backend/scripts/index_repo.py
```

Command:

```bash
python scripts/index_repo.py --repo-path ../sample-payment-service --repo-name sample-payment-service --branch main
```

Ye command local repo ko Elasticsearch me index karegi.

## Important boundary

Step 3 sirf repo indexing aur retrieval foundation banata hai.

Is step me ye cheeze intentionally nahi ki gayi:

```text
LangGraph workflow ko real retrieve_context se wire nahi kiya
PR review agent ko real RAG context use karna start nahi karaya
PostgreSQL me kuch save nahi kiya
Dependencies change nahi ki
```

Reason:

Workflow ko stable placeholder mode me rakhna tha, aur Step 3 ko isolated learning slice banana tha.

## One-line summary

Step 3 repo ko searchable memory me convert karta hai, jise later PR review workflow related context retrieve karne ke liye use karega.
