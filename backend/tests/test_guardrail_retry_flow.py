from app.graph.nodes import eval_judge_agent, finding_guardrail_node
from app.graph.routers import route_after_eval, route_after_finding_guardrail
from app.schemas.diff import DiffSummary, FileChangeSummary
from app.schemas.eval import EvalResult, FindingGuardrailResult, GuardrailIssue, GuardrailStatus
from app.schemas.finding import Finding
from app.schemas.pr import ChangedFile
from app.schemas.rag import ContextQualityResult
from app.schemas.risk import RiskSummary


def _state(findings: list) -> dict:
    return {
        "request_id": "req_guardrail_test",
        "workflow_mode": "live",
        "pr_url": "https://github.com/org/repo/pull/1",
        "pr_goal": "review payment change",
        "changed_files": [ChangedFile(filename="app/payment_service.py", status="modified")],
        "retrieved_context": [],
        "diff_summary": DiffSummary(
            review_mode="goal_aware",
            main_change_type="business_logic_change",
            main_area="payment",
            goal_detected=True,
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
        "retry_count": {
            "context_quality": 0,
            "finding_guardrail": 0,
            "eval_judge": 0,
            "scoring": 0,
        },
        "errors": [],
        "trace": [],
    }


def _finding(**overrides) -> Finding:
    data = {
        "file_path": "app/payment_service.py",
        "line_number": None,
        "severity": "medium",
        "issue": "Payment logic changed without a focused test.",
        "suggestion": "Add a test for calculate_final_amount with processing fee.",
        "pr_relevance_reason": "The changed file is part of this PR.",
        "relation_to_pr": "missing_test_for_changed_logic",
        "evidence": "app/payment_service.py changed payment calculation.",
    }
    data.update(overrides)
    return Finding(**data)


def test_finding_guardrail_passes_for_valid_finding():
    state = finding_guardrail_node(_state([_finding()]))

    assert state["guardrail_result"].pr_scope_passed
    assert state["guardrails"].hallucination_passed
    assert state["finding_guardrail_result"].passed


def test_pr_scope_guardrail_fails_for_unrelated_file():
    state = finding_guardrail_node(_state([_finding(file_path="legacy/old.py")]))

    assert not state["guardrail_result"].pr_scope_passed
    assert not state["finding_guardrail_result"].passed
    assert state["finding_guardrail_result"].rejected_finding_indexes == [0]


def test_evidence_guardrail_fails_for_missing_evidence():
    finding = _finding()
    finding.evidence = ""

    state = finding_guardrail_node(_state([finding]))

    assert not state["guardrail_result"].evidence_passed
    assert any(issue.guardrail_name == "evidence" for issue in state["finding_guardrail_result"].issues)


def test_hallucination_guardrail_fails_for_negative_line_number():
    state = finding_guardrail_node(_state([_finding(line_number=-1)]))

    assert not state["finding_guardrail_result"].passed
    assert any(issue.guardrail_name == "hallucination" for issue in state["finding_guardrail_result"].issues)


def test_severity_guardrail_fails_for_miscalibrated_critical():
    state = finding_guardrail_node(_state([_finding(severity="critical", issue="Minor style issue")]))

    assert not state["finding_guardrail_result"].passed
    assert any(issue.guardrail_name == "severity" for issue in state["finding_guardrail_result"].issues)


def test_suggestion_guardrail_fails_for_generic_suggestion():
    state = finding_guardrail_node(_state([_finding(suggestion="fix this")]))

    assert not state["finding_guardrail_result"].passed
    assert any(issue.guardrail_name == "suggestion" for issue in state["finding_guardrail_result"].issues)


def test_finding_retry_router_increments_and_routes_back():
    state = _state([])
    state["finding_guardrail_result"] = FindingGuardrailResult(
        passed=False,
        issues=[GuardrailIssue(guardrail_name="evidence", reason="Missing evidence")],
        rejected_finding_indexes=[0],
        retry_instruction="Fix evidence.",
    )

    route = route_after_finding_guardrail(state)

    assert route == "pr_review"
    assert state["retry_count"]["finding_guardrail"] == 1
    assert state["review_retry_instruction"] == "Fix evidence."


def test_finding_retry_router_proceeds_after_max_retry():
    state = _state([])
    state["retry_count"]["finding_guardrail"] = 3
    state["finding_guardrail_result"] = FindingGuardrailResult(
        passed=False,
        issues=[GuardrailIssue(guardrail_name="evidence", reason="Missing evidence")],
        rejected_finding_indexes=[0],
        retry_instruction="Fix evidence.",
    )

    assert route_after_finding_guardrail(state) == "eval_judge"
    assert state["retry_count"]["finding_guardrail"] == 3


def test_eval_judge_uses_mocked_structured_output(monkeypatch):
    class MockEvalLLM:
        def invoke(self, prompt: str):
            return EvalResult(
                score=82,
                passed=True,
                reason="Mock eval passed.",
                checks=["pr_related", "evidence_backed"],
            )

    state = _state([_finding()])
    state["guardrail_result"] = GuardrailStatus(
        pr_scope_passed=True,
        evidence_passed=True,
        hallucination_passed=True,
        score_passed=True,
    )
    state["finding_guardrail_result"] = FindingGuardrailResult(passed=True)
    monkeypatch.setattr("app.graph.nodes._get_structured_llm", lambda schema: MockEvalLLM())

    result = eval_judge_agent(state)

    assert result["eval_result"].score == 82
    assert result["eval_result"].passed


def test_eval_retry_router_and_max_retry():
    state = _state([])
    state["eval_result"] = EvalResult(
        score=50,
        passed=False,
        reason="Weak review.",
        improvement_instruction="Make findings more actionable.",
    )

    assert route_after_eval(state) == "pr_review"
    assert state["retry_count"]["eval_judge"] == 1
    assert state["eval_improvement_instruction"] == "Make findings more actionable."

    state["retry_count"]["eval_judge"] = 3
    assert route_after_eval(state) == "final_scoring"
