def retrieve_context_placeholder(query: str) -> list[str]:
    if not query:
        return []
    return ["RAG placeholder: real Elasticsearch retrieval will be implemented in a later phase."]
