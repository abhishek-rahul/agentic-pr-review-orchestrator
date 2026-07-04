from typing import Literal

from pydantic import BaseModel

from app.schemas.diff import DiffSummary
from app.schemas.eval import EvalResult, GuardrailStatus
from app.schemas.finding import Finding
from app.schemas.pr import ChangedFile, PRMetadata
from app.schemas.rag import ContextQualityResult, RAGQueryPlan, RetrievedContext
from app.schemas.risk import RiskSummary
from app.schemas.trace import TraceStep

RiskLevel = Literal["low", "medium", "high", "critical"]
Recommendation = Literal[
    "merge_ready",
    "merge_with_minor_fixes",
    "fix_before_merge",
    "do_not_merge",
]


class ReviewResult(BaseModel):
    request_id: str
    review_mode: str
    pr_url: str
    pr_metadata: PRMetadata
    changed_files: list[ChangedFile]
    diff_summary: DiffSummary
    risk_summary: RiskSummary
    rag_query_plan: RAGQueryPlan
    retrieved_context: list[RetrievedContext]
    context_quality: ContextQualityResult
    overall_score: int
    confidence: int
    risk_level: RiskLevel
    recommendation: Recommendation
    final_summary: str
    findings: list[Finding]
    guardrails: GuardrailStatus
    eval_result: EvalResult
    trace: list[TraceStep]
