import asyncio
import json

from app.graph.workflow import build_review_graph
from app.schemas.diff import DiffSummary, FileChangeSummary
from app.schemas.finding import Finding, FindingList
from app.schemas.pr import ChangedFile, PRMetadata
from app.schemas.risk import RiskSummary

EXPECTED_RETRY_COUNT = {
    "context_quality": 0,
    "finding_guardrail": 0,
    "eval_judge": 0,
    "scoring": 0,
}

EXPECTED_TRACE = [
    ("S6A.1", "parse_pr_url_node"),
    ("S6A.2", "fetch_pr_data_node"),
    ("S6A.3", "diff_understanding_agent"),
    ("S6A.4", "risk_classification_agent"),
    ("S6A.5", "rag_query_planner_agent"),
    ("S6A.6", "rag_retriever_node"),
    ("S6A.7", "context_quality_agent"),
    ("S6A.8", "pr_review_agent"),
    ("S6A.9", "finding_guardrail_node"),
    ("S6A.10", "eval_judge_agent"),
    ("S6A.11", "final_scoring_agent"),
    ("S6A.12", "response_builder_node"),
]


class FakeStructuredLLM:
    def __init__(self, outputs: dict):
        self.outputs = outputs

    def invoke(self, prompt: str):
        if "DiffSummary" in prompt:
            return self.outputs["diff"]
        if "RiskSummary" in prompt or "Classify PR risk" in prompt:
            return self.outputs["risk"]
        return self.outputs["findings"]


def _run_workflow(state: dict) -> dict:
    return asyncio.run(build_review_graph().ainvoke(state))


def _initial_state(workflow_mode: str | None = "live") -> dict:
    state = {
        "request_id": "req_live_test",
        "pr_url": "https://github.com/abhishek-rahul/sample-payment-service/pull/1",
        "pr_goal": "review payment validation",
        "retry_count": EXPECTED_RETRY_COUNT.copy(),
        "errors": [],
        "trace": [],
    }
    if workflow_mode is not None:
        state["workflow_mode"] = workflow_mode
    return state


def _trace_pairs(result: dict) -> list[tuple[str, str]]:
    return [(item.step_id, item.agent_id) for item in result["trace"]]


def _mock_github(monkeypatch, files: list[ChangedFile]) -> None:
    async def fake_metadata(pr_ref):
        return PRMetadata(
            title="Mock PR",
            author="octocat",
            base_branch="main",
            head_branch="feature",
            state="open",
            additions=sum(file.additions for file in files),
            deletions=sum(file.deletions for file in files),
            changed_files_count=len(files),
        )

    async def fake_files(pr_ref):
        return files

    monkeypatch.setattr("app.graph.nodes.fetch_pr_metadata", fake_metadata)
    monkeypatch.setattr("app.graph.nodes.fetch_changed_files", fake_files)


def _mock_llm(monkeypatch, diff: DiffSummary, risk: RiskSummary, findings: list[Finding]) -> None:
    outputs = {
        "diff": diff,
        "risk": risk,
        "findings": FindingList(findings=findings),
    }
    monkeypatch.setattr("app.graph.nodes._get_structured_llm", lambda schema: FakeStructuredLLM(outputs))


def _diff_summary(change_type: str = "business_logic_change", area: str = "payment") -> DiffSummary:
    return DiffSummary(
        review_mode="goal_aware",
        main_change_type=change_type,
        main_area=area,
        goal_detected=True,
        files=[
            FileChangeSummary(
                file_path="app/payment_service.py",
                change_type="business_logic",
                summary="Payment validation changed.",
                risk_hint="high",
            )
        ],
        requires_rag=False,
        required_review_types=["business_logic", "test_impact"],
    )


def _risk_summary(risk: str = "high") -> RiskSummary:
    return RiskSummary(
        overall_risk=risk,
        risk_reasons=["Payment validation changed"],
        required_review_types=["business_logic", "test_impact"],
    )


def _high_finding() -> Finding:
    return Finding(
        file_path="app/payment_service.py",
        line_number=None,
        severity="high",
        issue="Validation logic appears to be removed.",
        suggestion="Restore validation or add a focused regression test.",
        pr_relevance_reason="The changed diff removes validation-related logic.",
        relation_to_pr="introduced_by_pr",
        evidence="The PR diff removes a validation check.",
    )


def test_live_workflow_uses_mocked_github_and_llm(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _mock_github(
        monkeypatch,
        [
            ChangedFile(
                filename="app/payment_service.py",
                status="modified",
                additions=5,
                deletions=2,
                patch="- validate_coupon(expiry)\n+ apply_coupon(coupon)",
            )
        ],
    )
    _mock_llm(monkeypatch, _diff_summary(), _risk_summary(), [_high_finding()])
    monkeypatch.setattr("app.rag.retriever.retrieve_context", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))

    result = _run_workflow(_initial_state())

    assert result["final_response"]["request_id"] == "req_live_test"
    assert result["final_response"]["recommendation"] == "fix_before_merge"
    assert result["final_response"]["findings"][0]["severity"] == "high"


def test_live_workflow_final_response_shape_and_trace():
    result = _run_with_docs_only()
    response = result["final_response"]

    json.dumps(response)
    assert set(response) == {
        "request_id",
        "pr_url",
        "review_mode",
        "overall_score",
        "confidence",
        "risk_level",
        "recommendation",
        "summary",
        "findings",
        "trace",
        "errors",
    }
    assert _trace_pairs(result) == EXPECTED_TRACE
    assert [(item["step_id"], item["agent_id"]) for item in response["trace"]] == EXPECTED_TRACE


def test_missing_workflow_mode_behaves_as_live(monkeypatch):
    _mock_github(
        monkeypatch,
        [ChangedFile(filename="docs/readme.md", status="modified", patch="+ docs")],
    )
    _mock_llm(
        monkeypatch,
        _diff_summary("docs_change", "documentation"),
        _risk_summary("low"),
        [],
    )

    result = _run_workflow(_initial_state(workflow_mode=None))

    assert _trace_pairs(result)[0] == ("S6A.1", "parse_pr_url_node")
    assert result["final_response"]["recommendation"] == "merge_ready"


def test_docs_only_has_no_findings_and_high_score():
    result = _run_with_docs_only()

    assert result["final_response"]["findings"] == []
    assert result["final_response"]["overall_score"] >= 85
    assert result["final_response"]["recommendation"] == "merge_ready"


def test_validation_removal_gets_high_risk(monkeypatch):
    _mock_github(
        monkeypatch,
        [
            ChangedFile(
                filename="app/payment_service.py",
                status="modified",
                patch="- if coupon.is_expired: raise ValidationError\n+ return discount",
            )
        ],
    )
    _mock_llm(monkeypatch, _diff_summary(), _risk_summary("high"), [_high_finding()])

    result = _run_workflow(_initial_state())

    assert result["final_response"]["risk_level"] == "high"
    assert result["final_response"]["recommendation"] == "fix_before_merge"


def _run_with_docs_only() -> dict:
    from app.graph import nodes

    async def fake_metadata(pr_ref):
        return PRMetadata(
            title="Update docs",
            author="octocat",
            base_branch="main",
            head_branch="docs",
            state="open",
            additions=2,
            deletions=0,
            changed_files_count=1,
        )

    async def fake_files(pr_ref):
        return [ChangedFile(filename="docs/readme.md", status="modified", patch="+ update docs")]

    original_metadata = nodes.fetch_pr_metadata
    original_files = nodes.fetch_changed_files
    original_structured = nodes._get_structured_llm

    nodes.fetch_pr_metadata = fake_metadata
    nodes.fetch_changed_files = fake_files
    nodes._get_structured_llm = lambda schema: FakeStructuredLLM(
        {
            "diff": _diff_summary("docs_change", "documentation"),
            "risk": _risk_summary("low"),
            "findings": FindingList(findings=[]),
        }
    )
    try:
        return _run_workflow(_initial_state())
    finally:
        nodes.fetch_pr_metadata = original_metadata
        nodes.fetch_changed_files = original_files
        nodes._get_structured_llm = original_structured
