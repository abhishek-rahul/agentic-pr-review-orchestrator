from typing import TypedDict

from app.schemas.diff import DiffSummary
from app.schemas.eval import EvalResult, GuardrailStatus
from app.schemas.finding import Finding
from app.schemas.pr import ChangedFile, PRMetadata, PRRef
from app.schemas.rag import ContextQualityResult, RAGQueryPlan, RetrievedContext
from app.schemas.risk import RiskSummary
from app.schemas.trace import TraceStep


class PRReviewState(TypedDict, total=False):
    request_id: str
    pr_url: str
    pr_goal: str | None

    pr_ref: PRRef
    pr_metadata: PRMetadata
    changed_files: list[ChangedFile]

    diff_summary: DiffSummary
    risk_summary: RiskSummary
    rag_query_plan: RAGQueryPlan
    retrieved_context: list[RetrievedContext]
    context_quality: ContextQualityResult

    findings: list[Finding]
    guardrails: GuardrailStatus
    eval_result: EvalResult

    overall_score: int
    confidence: int
    risk_level: str
    recommendation: str
    final_summary: str

    trace: list[TraceStep]
