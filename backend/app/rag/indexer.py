import hashlib
from typing import Any

from app.ai.embedding_gateway import get_embeddings
from app.config import get_settings
from app.schemas.rag import RepoChunk

INDEX_NAME = "pr-review-repo-context"


def index_documents_placeholder(documents: list[str]) -> int:
    return len(documents)

# ye function repo ke chunks ko index krta h elasticsearch me 
# ensure krta h ki index exist krta h ya nhi agar nhi to create krta h
# documment id generate krta h repo name, branch aur chunk id se aur phir bulk me index krta h
def index_repo_chunks(repo_name: str, branch: str, chunks: list[RepoChunk]) -> int:
    if not chunks:
        return 0

    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk

    embeddings = get_embeddings()
    vectors = embeddings.embed_documents([chunk.content for chunk in chunks])
    if not vectors:
        return 0

    client = Elasticsearch(get_settings().elasticsearch_url)
    _ensure_index(client, len(vectors[0]))

    actions = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        actions.append(
            {
                "_index": INDEX_NAME,
                "_id": _document_id(repo_name, branch, chunk.chunk_id),
                "_source": {
                    "repo_name": repo_name,
                    "branch": branch,
                    "file_path": chunk.file_path,
                    "chunk_id": chunk.chunk_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "content_vector": vector,
                },
            }
        )

    success_count, _ = bulk(client, actions)
    return success_count


def _ensure_index(client: Any, vector_dims: int) -> None:
    if client.indices.exists(index=INDEX_NAME):
        return

    client.indices.create(
        index=INDEX_NAME,
        mappings={
            "properties": {
                "repo_name": {"type": "keyword"},
                "branch": {"type": "keyword"},
                "file_path": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
                "content": {"type": "text"},
                "content_vector": {
                    "type": "dense_vector",
                    "dims": vector_dims,
                    "index": True,
                    "similarity": "cosine",
                },
            }
        },
    )


def _document_id(repo_name: str, branch: str, chunk_id: str) -> str:
    raw_id = f"{repo_name}:{branch}:{chunk_id}"
    return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()
