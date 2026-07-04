from app.ai.embedding_gateway import get_embeddings
from app.config import get_settings
from app.rag.indexer import INDEX_NAME
from app.schemas.rag import RetrievedContext


def retrieve_context_placeholder(query: str) -> list[str]:
    if not query:
        return []
    return ["RAG placeholder: real Elasticsearch retrieval will be implemented in a later phase."]


def retrieve_context(
    query: str,
    repo_name: str,
    branch: str,
    top_k: int = 6,
) -> list[RetrievedContext]:
    if not query.strip():
        return []

    from elasticsearch import Elasticsearch

    client = Elasticsearch(get_settings().elasticsearch_url)
    if not client.indices.exists(index=INDEX_NAME):
        return []

    query_vector = get_embeddings().embed_query(query)
    response = client.search(
        index=INDEX_NAME,
        size=top_k,
        query={
            "script_score": {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"repo_name": repo_name}},
                            {"term": {"branch": branch}},
                        ]
                    }
                },
                "script": {
                    "source": "cosineSimilarity(params.query_vector, 'content_vector') + 1.0",
                    "params": {"query_vector": query_vector},
                },
            }
        },
    )

    contexts: list[RetrievedContext] = []
    for hit in response.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        contexts.append(
            RetrievedContext(
                file_path=source.get("file_path", ""),
                content=source.get("content", ""),
                reason=f"Matched repo context for query: {query}",
                score=float(hit.get("_score", 0.0)),
            )
        )

    return contexts
