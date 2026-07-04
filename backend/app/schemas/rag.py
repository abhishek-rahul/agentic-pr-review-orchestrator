from pydantic import BaseModel


class RAGQuery(BaseModel):
    query: str
    purpose: str


class RAGQueryPlan(BaseModel):
    queries: list[RAGQuery]
    top_k: int = 6


class RetrievedContext(BaseModel):
    file_path: str
    content: str
    reason: str
    score: float = 0.0


class ContextQualityResult(BaseModel):
    context_enough: bool
    reason: str
    missing_context: list[str]
    suggested_queries: list[str]
