from app.guardrails.evidence import validate_evidence
from app.guardrails.hallucination import validate_file_paths
from app.guardrails.pr_scope import validate_pr_scope
from app.schemas.finding import Finding
from app.schemas.pr import ChangedFile


def test_guardrails_pass_for_changed_file_finding():
    changed_files = [ChangedFile(filename="app/service.py", status="modified")]
    findings = [
        Finding(
            file_path="app/service.py",
            severity="medium",
            issue="Missing test for changed logic.",
            suggestion="Add a focused test.",
            pr_relevance_reason="The file is changed in this PR.",
            relation_to_pr="missing_test_for_changed_logic",
            evidence="app/service.py was modified.",
        )
    ]

    assert validate_pr_scope(findings, changed_files)
    assert validate_evidence(findings)
    assert validate_file_paths(findings, changed_files)


def test_pr_scope_fails_for_unchanged_file():
    changed_files = [ChangedFile(filename="app/service.py", status="modified")]
    findings = [
        Finding(
            file_path="legacy/old.py",
            severity="low",
            issue="Legacy issue.",
            suggestion="Ignore in PR review.",
            pr_relevance_reason="Not related.",
            relation_to_pr="modified_by_pr",
            evidence="No changed file evidence.",
        )
    ]

    assert not validate_pr_scope(findings, changed_files)
