from app.graph.nodes import final_scoring_agent, score_guardrail_node
from app.graph.routers import route_after_score_guardrail
from app.schemas.diff import DiffSummary, FileChangeSummary
from app.schemas.eval import (
    EvalResult,
    FindingGuardrailResult,
    GuardrailIssue,
    GuardrailStatus,
    ScoreGuardrailResult,
)
from app.schemas.finding import Finding
from app.schemas.pr import ChangedFile
from app.schemas.rag import ContextQualityResult
from app.schemas.risk import RiskSummary


def _finding(severity: str = "medium", relation: str = "missing_test_for_changed_logic") -> Finding:
    return Finding(
        file_path="app/payment_service.py",
        line_number=None,
        severity=severity,
        issue="Payment logic changed without enough coverage.",
        suggestion="Add a test for calculate_final_amount with processing fee.",
        pr_relevance_reason="The changed file is part of this PR.",
        relation_to_pr=relation,
        evidence="app/payment_service.py changed payment calculation.",
    )


def _state(findings: list[Finding]) -> dict:
    return {
        "request_id": "req_score_test",
        "workflow_mode": "live",
        "pr_url": "https://github.com/org/repo/pull/1",
        "changed_files": [ChangedFile(filename="app/payment_service.py", status="modified")],
        "diff_summary": DiffSummary(
            review_mode="generic",
            main_change_type="business_logic_change",
            main_area="payment",
            goal_detected=False,
            files=[
                FileChangeSummary(
                    file_path="app/payment_service.py",
                    change_type="business_logic",
                    summary="Payment logic changed.",
                    risk_hint="high",
                )
            ],
            requires_rag=True,
            required_review_types=["business_logic", "test_impact"],
        ),
        "risk_summary": RiskSummary(
            overall_risk="high",
            risk_reasons=["Payment calculation changed"],
            required_review_types=["business_logic", "test_impact"],
        ),
        "context_quality": ContextQualityResult(
            context_enough=True,
            reason="Mock context enough.",
            missing_context=[],
            suggested_queries=[],
        ),
        "findings": findings,
        "guardrail_result": GuardrailStatus(
            pr_scope_passed=True,
            evidence_passed=True,
            hallucination_passed=True,
            score_passed=True,
        ),
        "finding_guardrail_result": FindingGuardrailResult(passed=True),
        "eval_result": EvalResult(score=90, passed=True, reason="Mock eval passed."),
        "retry_count": {
            "context_quality": 0,
            "finding_guardrail": 0,
            "eval_judge": 0,
            "scoring": 0,
        },
        "errors": [],
        "trace": [],
    }


def test_scoring_penalizes_high_and_medium_findings():
    state = final_scoring_agent(_state([_finding("high", "introduced_by_pr"), _finding("medium")]))

    assert state["overall_score"] < 80
    assert state["risk_level"] == "high"
    assert state["recommendation"] == "fix_before_merge"
    assert state["score_breakdown"].test_coverage < 100


def test_critical_finding_needs_human_review():
    state = final_scoring_agent(_state([_finding("critical", "introduced_by_pr")]))

    assert state["risk_level"] == "critical"
    assert state["recommendation"] == "needs_human_review"


def test_score_guardrail_passes_consistent_score():
    state = final_scoring_agent(_state([_finding("medium")]))
    state = score_guardrail_node(state)

    assert state["score_guardrail_result"].passed
    assert state["guardrail_result"].score_passed


def test_score_guardrail_fails_inconsistent_merge_ready():
    state = _state([_finding("high", "introduced_by_pr")])
    state["overall_score"] = 95
    state["confidence"] = 90
    state["risk_level"] = "low"
    state["recommendation"] = "merge_ready"
    state["score_breakdown"] = final_scoring_agent(_state([]))["score_breakdown"]

    state = score_guardrail_node(state)

    assert not state["score_guardrail_result"].passed
    assert any("merge_ready" in issue.reason for issue in state["score_guardrail_result"].issues)


def test_score_retry_router_and_max_retry():
    state = _state([])
    state["score_guardrail_result"] = ScoreGuardrailResult(
        passed=False,
        issues=[GuardrailIssue(guardrail_name="score_guardrail", reason="Bad score")],
        retry_instruction="Recalculate score.",
    )

    assert route_after_score_guardrail(state) == "final_scoring"
    assert state["retry_count"]["scoring"] == 1
    assert state["scoring_retry_instruction"] == "Recalculate score."

    state["retry_count"]["scoring"] = 3
    assert route_after_score_guardrail(state) == "response_builder"
