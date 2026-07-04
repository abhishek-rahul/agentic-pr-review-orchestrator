# Step 3 Function Calling Flow

## Big Picture

Step 3 ka main flow ye hai:

```text
CLI command
  -> index_repo.py
  -> index_local_repo()
  -> load_repo_files()
  -> split_repo_file()
  -> index_repo_chunks()
  -> get_embeddings()
  -> Elasticsearch
```

Simple terms me:

```text
Repo folder do
  -> files load karo
  -> files ko chunks me todo
  -> chunks ke embeddings banao
  -> Elasticsearch me save karo
```

## 1. Manual CLI Se Flow Start Hota Hai

File:

```text
backend/scripts/index_repo.py
```

Command:

```bash
python scripts/index_repo.py --repo-path ../sample-payment-service --repo-name sample-payment-service --branch main
```

Function call:

```python
main()
```

`main()` kya karta hai:

1. CLI args read karta hai.
2. `repo_path`, `repo_name`, `branch` nikalta hai.
3. `index_local_repo(...)` call karta hai.

Code flow:

```text
main()
  -> index_local_repo(args.repo_path, args.repo_name, args.branch)
```

## 2. High-Level Orchestration

File:

```text
backend/app/rag/repo_index_service.py
```

Function:

```python
index_local_repo(repo_path: str, repo_name: str, branch: str = "main") -> int
```

Ye Step 3 ka main service function hai.

Function calling:

```text
index_local_repo()
  -> os.path.isdir(repo_path)
  -> load_repo_files(repo_path)
  -> split_repo_file(repo_file) for each file
  -> index_repo_chunks(repo_name, branch, chunks)
```

Simple terms:

1. Pehle check karta hai repo path valid folder hai ya nahi.
2. Repo ke useful files load karta hai.
3. Har file ko chunks me split karta hai.
4. Saare chunks Elasticsearch me index karta hai.
5. Indexed chunks ka count return karta hai.

## 3. File Loading Flow

File:

```text
backend/app/rag/file_loader.py
```

Function:

```python
load_repo_files(repo_path: str) -> list[RepoFile]
```

Function calling:

```text
load_repo_files()
  -> os.path.isdir(repo_path)
  -> os.walk(repo_path)
  -> _should_load_file(file_name)
  -> _read_text_file(full_path)
  -> RepoFile(file_path=relative_path, content=content)
```

### 3.1 `load_repo_files()` kya karta hai

Ye repo folder ke andar recursively files dekhta hai.

Skipped folders:

```text
.git
.venv
__pycache__
.pytest_cache
node_modules
dist
build
```

Allowed file extensions:

```text
.py
.md
.txt
.toml
.yaml
.yml
.json
```

### 3.2 `_should_load_file()` call

Function:

```python
_should_load_file(file_name: str) -> bool
```

Ye decide karta hai file load karni hai ya skip.

Skip examples:

```text
.env
.pyc
.png
.jpg
.zip
```

Flow:

```text
file_name
  -> lowercase
  -> extension check
  -> skip list check
  -> allowed extension check
```

### 3.3 `_read_text_file()` call

Function:

```python
_read_text_file(file_path: str) -> str | None
```

Ye file ko binary mode me read karta hai, phir safe text banata hai.

Flow:

```text
open file as bytes
  -> if read error: return None
  -> if NUL byte found: return None
  -> decode UTF-8
  -> if decode fail: return None
  -> return text content
```

Important:

Binary files aur unreadable files skip ho jate hain.

## 4. Text Splitting Flow

File:

```text
backend/app/rag/text_splitter.py
```

Function:

```python
split_repo_file(repo_file: RepoFile, chunk_size: int = 1200, overlap: int = 150) -> list[RepoChunk]
```

Function calling:

```text
split_repo_file()
  -> _validate_split_settings(chunk_size, overlap)
  -> check empty/whitespace content
  -> calculate step_size = chunk_size - overlap
  -> loop over content
  -> create RepoChunk(...)
```

### 4.1 `_validate_split_settings()` call

Function:

```python
_validate_split_settings(chunk_size: int, overlap: int) -> None
```

Validation rules:

```text
chunk_size > 0
overlap >= 0
overlap < chunk_size
```

Invalid hua to `ValueError`.

### 4.2 Chunk creation

For each file:

```text
RepoFile(file_path="app/service.py", content="long text...")
```

Output:

```text
RepoChunk(file_path="app/service.py", chunk_id="app/service.py:0", chunk_index=0, content="...")
RepoChunk(file_path="app/service.py", chunk_id="app/service.py:1", chunk_index=1, content="...")
```

`chunk_id` format:

```text
{file_path}:{chunk_index}
```

## 5. Elasticsearch Indexing Flow

File:

```text
backend/app/rag/indexer.py
```

Function:

```python
index_repo_chunks(repo_name: str, branch: str, chunks: list[RepoChunk]) -> int
```

Function calling:

```text
index_repo_chunks()
  -> if chunks empty: return 0
  -> get_embeddings()
  -> embeddings.embed_documents([...chunk.content...])
  -> Elasticsearch(get_settings().elasticsearch_url)
  -> _ensure_index(client, vector_dims)
  -> _document_id(repo_name, branch, chunk.chunk_id)
  -> bulk(client, actions)
  -> return success_count
```

### 5.1 Embeddings call

Function:

```python
get_embeddings()
```

Source:

```text
backend/app/ai/embedding_gateway.py
```

Important:

RAG code direct `OpenAIEmbeddings` instantiate nahi karta. RAG code sirf gateway use karta hai.

Flow:

```text
chunks
  -> chunk.content list
  -> embeddings.embed_documents(...)
  -> vectors
```

### 5.2 Elasticsearch client

Function call:

```python
Elasticsearch(get_settings().elasticsearch_url)
```

Settings source:

```text
backend/app/config.py
```

Env value:

```text
ELASTICSEARCH_URL=http://localhost:9200
```

### 5.3 Index creation

Function:

```python
_ensure_index(client, vector_dims)
```

Ye check karta hai:

```text
index exists?
  -> yes: do nothing
  -> no: create index with mapping
```

Index name:

```text
pr-review-repo-context
```

Mapping fields:

```text
repo_name keyword
branch keyword
file_path keyword
chunk_id keyword
chunk_index integer
content text
content_vector dense_vector
```

### 5.4 Document ID creation

Function:

```python
_document_id(repo_name, branch, chunk_id)
```

Flow:

```text
repo_name:branch:chunk_id
  -> sha256
  -> deterministic Elasticsearch document id
```

Benefit:

Same repo, branch, chunk dobara index hua to same document overwrite hoga.

### 5.5 Bulk indexing

Function:

```python
bulk(client, actions)
```

Har action me ye fields save hoti hain:

```text
repo_name
branch
file_path
chunk_id
chunk_index
content
content_vector
```

## 6. Real Retrieval Flow

File:

```text
backend/app/rag/retriever.py
```

Function:

```python
retrieve_context(query: str, repo_name: str, branch: str, top_k: int = 6) -> list[RetrievedContext]
```

Function calling:

```text
retrieve_context()
  -> if blank query: return []
  -> Elasticsearch(get_settings().elasticsearch_url)
  -> if index missing: return []
  -> get_embeddings().embed_query(query)
  -> client.search(...)
  -> convert hits to RetrievedContext
  -> return contexts
```

Simple terms:

1. User/agent query deta hai.
2. Query ka embedding banta hai.
3. Elasticsearch me same repo and branch ke chunks search hote hain.
4. Matching chunks `RetrievedContext` me return hote hain.

Filter:

```text
repo_name exact match
branch exact match
```

Reason field:

```text
Matched repo context for query: {query}
```

## 7. Current Workflow Placeholder Flow

File:

```text
backend/app/graph/nodes.py
```

Current workflow abhi real `retrieve_context()` use nahi karta.

Current call:

```text
rag_retriever_node()
  -> retrieve_context_placeholder(item.query)
```

Placeholder function:

```python
retrieve_context_placeholder(query: str) -> list[str]
```

Reason:

Step 3 me indexing foundation banaya gaya. Workflow ko real retrieval se wire karna later step me hoga.

## Full Indexing Call Tree

```text
python scripts/index_repo.py --repo-path ... --repo-name ... --branch ...
  -> main()
    -> index_local_repo(repo_path, repo_name, branch)
      -> os.path.isdir(repo_path)
      -> load_repo_files(repo_path)
        -> os.path.isdir(repo_path)
        -> os.walk(repo_path)
        -> _should_load_file(file_name)
        -> _read_text_file(full_path)
        -> RepoFile(...)
      -> split_repo_file(repo_file)
        -> _validate_split_settings(chunk_size, overlap)
        -> RepoChunk(...)
      -> index_repo_chunks(repo_name, branch, chunks)
        -> get_embeddings()
        -> embeddings.embed_documents(...)
        -> Elasticsearch(...)
        -> _ensure_index(client, vector_dims)
        -> _document_id(repo_name, branch, chunk_id)
        -> bulk(client, actions)
      -> return indexed chunk count
```

## Full Retrieval Call Tree

```text
retrieve_context(query, repo_name, branch, top_k)
  -> if query blank: return []
  -> Elasticsearch(...)
  -> client.indices.exists(...)
  -> get_embeddings()
  -> embeddings.embed_query(query)
  -> client.search(...)
  -> RetrievedContext(...)
  -> return list[RetrievedContext]
```

## Data Object Flow

```text
RepoFile
  file_path
  content

RepoChunk
  file_path
  chunk_id
  chunk_index
  content

Elasticsearch document
  repo_name
  branch
  file_path
  chunk_id
  chunk_index
  content
  content_vector

RetrievedContext
  file_path
  content
  reason
  score
```

## One-Line Summary

Step 3 ka function calling flow local repo ko `RepoFile` se `RepoChunk`, phir embedding vector, phir Elasticsearch document me convert karta hai; retrieval side query ko embedding banakar same repo/branch ke matching chunks wapas laati hai.
