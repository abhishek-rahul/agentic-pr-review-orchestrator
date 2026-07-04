from typing import Any, Literal, TypedDict

from app.schemas.diff import DiffSummary
from app.schemas.eval import EvalResult, GuardrailStatus
from app.schemas.finding import Finding
from app.schemas.pr import ChangedFile, PRMetadata, PRRef
from app.schemas.rag import ContextQualityResult, RAGQueryPlan, RetrievedContext
from app.schemas.risk import RiskSummary
from app.schemas.trace import TraceStep


class PRReviewState(TypedDict, total=False):
    request_id: str
    workflow_mode: Literal["skeleton"] | str
    pr_url: str
    pr_goal: str | None

    pr_ref: PRRef
    owner: str
    repo: str
    pr_number: int
    pr_metadata: PRMetadata
    changed_files: list[ChangedFile]
    raw_diff: str

    diff_summary: DiffSummary
    risk_summary: RiskSummary
    rag_query_plan: RAGQueryPlan
    retrieved_context: list[RetrievedContext]
    context_quality: ContextQualityResult

    findings: list[Finding]
    guardrail_result: GuardrailStatus
    guardrails: GuardrailStatus
    eval_result: EvalResult
    score_result: dict[str, Any]
    final_response: dict[str, Any]

    overall_score: int
    confidence: int
    risk_level: str
    recommendation: str
    final_summary: str

    retry_count: dict[str, int]
    errors: list[dict[str, str]]
    trace: list[TraceStep]
