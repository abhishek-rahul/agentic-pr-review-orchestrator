from app.evals.rule_eval import run_rule_eval
from app.github.client import fetch_changed_files, fetch_pr_metadata
from app.github.parser import parse_pr_url
from app.graph.debug import add_trace
from app.graph.state import PRReviewState
from app.guardrails.evidence import validate_evidence
from app.guardrails.hallucination import validate_file_paths
from app.guardrails.pr_scope import validate_pr_scope
from app.guardrails.scoring import validate_score
from app.rag.retriever import retrieve_context_placeholder
from app.schemas.diff import DiffSummary, FileChangeSummary
from app.schemas.eval import GuardrailStatus
from app.schemas.finding import Finding
from app.schemas.pr import ChangedFile, PRMetadata
from app.schemas.rag import ContextQualityResult, RAGQuery, RAGQueryPlan, RetrievedContext
from app.schemas.risk import RiskSummary

SOURCE_EXTENSIONS = (".py", ".js", ".ts", ".tsx", ".java", ".go")
TEST_HINTS = ("test", "spec")


def parse_pr_url_node(state: PRReviewState) -> PRReviewState:
    pr_ref = parse_pr_url(state["pr_url"])
    state["pr_ref"] = pr_ref
    state["owner"] = pr_ref.owner
    state["repo"] = pr_ref.repo
    state["pr_number"] = pr_ref.pr_number
    add_trace(state, "S5.1", "parse_pr_url_node", "passed", "PR URL parsed")
    return state


async def fetch_pr_data_node(state: PRReviewState) -> PRReviewState:
    pr_ref = state["pr_ref"]
    if state.get("workflow_mode") == "skeleton":
        state["pr_metadata"] = PRMetadata(
            title=f"Skeleton PR #{pr_ref.pr_number}",
            author="skeleton",
            base_branch="main",
            head_branch="skeleton-step-5",
            state="open",
            additions=12,
            deletions=3,
            changed_files_count=1,
        )
        state["changed_files"] = [
            ChangedFile(
                filename="app/payment_service.py",
                status="modified",
                additions=12,
                deletions=3,
                patch="@@ skeleton diff @@\n+ placeholder payment change\n",
            )
        ]
        state["raw_diff"] = "@@ skeleton diff @@\n+ placeholder payment change\n"
        add_trace(
            state,
            "S5.2",
            "fetch_pr_data_node",
            "passed",
            "Loaded skeleton PR data without GitHub API",
        )
        return state

    state["pr_metadata"] = await fetch_pr_metadata(pr_ref)
    state["changed_files"] = await fetch_changed_files(pr_ref)
    state["raw_diff"] = "\n".join(file.patch or "" for file in state["changed_files"])
    add_trace(
        state,
        "S5.2",
        "fetch_pr_data_node",
        "passed",
        f"Fetched {len(state['changed_files'])} changed file(s) from GitHub",
    )
    return state


def diff_understanding_agent(state: PRReviewState) -> PRReviewState:
    files = state.get("changed_files", [])
    file_summaries = [_summarize_file(file.filename) for file in files]

    has_docs = file_summaries and all(file.change_type == "docs" for file in file_summaries)
    has_config = any(file.change_type in {"config", "dependency"} for file in file_summaries)
    has_tests_only = file_summaries and all(file.change_type == "test" for file in file_summaries)
    has_business_logic = any(file.change_type in {"business_logic", "model"} for file in file_summaries)

    if has_docs:
        main_change_type = "docs_change"
        main_area = "documentation"
    elif has_tests_only:
        main_change_type = "test_change"
        main_area = "tests"
    elif has_config:
        main_change_type = "config_change"
        main_area = "configuration"
    elif has_business_logic:
        main_change_type = "business_logic_change"
        main_area = _guess_main_area([file.file_path for file in file_summaries])
    else:
        main_change_type = "mixed_change"
        main_area = "mixed"

    state["diff_summary"] = DiffSummary(
        review_mode="goal_aware" if state.get("pr_goal") else "generic",
        main_change_type=main_change_type,
        main_area=main_area,
        goal_detected=bool(state.get("pr_goal")),
        files=file_summaries,
        requires_rag=not has_docs,
        required_review_types=_required_review_types(main_change_type),
    )
    add_trace(
        state,
        "S5.3",
        "diff_understanding_agent",
        "passed",
        f"Detected {main_change_type} in {main_area}",
    )
    return state


def risk_classification_agent(state: PRReviewState) -> PRReviewState:
    summary = state["diff_summary"]

    if summary.main_change_type == "docs_change":
        risk = "low"
        reasons = ["Only documentation files changed"]
    elif summary.main_area in {"payment", "auth", "security"}:
        risk = "high"
        reasons = [f"Sensitive area changed: {summary.main_area}"]
    elif summary.main_change_type == "business_logic_change":
        risk = "medium"
        reasons = ["Business logic changed"]
    else:
        risk = "medium"
        reasons = ["Mixed or configuration changes require review"]

    state["risk_summary"] = RiskSummary(
        overall_risk=risk,
        risk_reasons=reasons,
        required_review_types=summary.required_review_types,
    )
    add_trace(state, "S5.4", "risk_classification_agent", "passed", f"Risk classified as {risk}")
    return state


def rag_query_planner_agent(state: PRReviewState) -> PRReviewState:
    summary = state["diff_summary"]
    queries: list[RAGQuery] = []

    if not summary.requires_rag:
        state["rag_query_plan"] = RAGQueryPlan(queries=[], top_k=0)
        add_trace(state, "S5.5", "rag_query_planner_agent", "skipped", "RAG not required")
        return state

    changed_paths = " ".join(file.file_path for file in summary.files)
    queries.append(
        RAGQuery(
            query=f"{summary.main_area} related implementation patterns {changed_paths}",
            purpose="Find related source code patterns",
        )
    )
    queries.append(
        RAGQuery(
            query=f"{summary.main_area} tests edge cases validation",
            purpose="Find related tests and edge cases",
        )
    )

    if state.get("pr_goal"):
        queries.append(
            RAGQuery(
                query=state["pr_goal"] or "",
                purpose="Find context related to the PR goal",
            )
        )

    state["rag_query_plan"] = RAGQueryPlan(queries=queries, top_k=6)
    add_trace(state, "S5.5", "rag_query_planner_agent", "passed", f"Planned {len(queries)} RAG query(ies)")
    return state


def rag_retriever_node(state: PRReviewState) -> PRReviewState:
    plan = state.get("rag_query_plan")
    if not plan or not plan.queries:
        state["retrieved_context"] = []
        add_trace(state, "S5.6", "rag_retriever_node", "skipped", "No RAG queries to execute")
        return state

    contexts: list[RetrievedContext] = []
    for item in plan.queries[: plan.top_k]:
        for raw_context in retrieve_context_placeholder(item.query):
            contexts.append(
                RetrievedContext(
                    file_path="rag/placeholder.txt",
                    content=raw_context,
                    reason=item.purpose,
                    score=0.0,
                )
            )

    state["retrieved_context"] = contexts[: plan.top_k]
    add_trace(
        state,
        "S5.6",
        "rag_retriever_node",
        "passed",
        f"Retrieved {len(state['retrieved_context'])} context chunk(s)",
    )
    return state


def context_quality_agent(state: PRReviewState) -> PRReviewState:
    summary = state["diff_summary"]
    contexts = state.get("retrieved_context", [])

    if not summary.requires_rag:
        result = ContextQualityResult(
            context_enough=True,
            reason="RAG was not required for this PR type.",
            missing_context=[],
            suggested_queries=[],
        )
    elif contexts:
        result = ContextQualityResult(
            context_enough=True,
            reason="At least one related context chunk was retrieved.",
            missing_context=[],
            suggested_queries=[],
        )
    else:
        result = ContextQualityResult(
            context_enough=False,
            reason="No related context was retrieved.",
            missing_context=["repo context"],
            suggested_queries=[summary.main_area],
        )

    state["context_quality"] = result
    status = "passed" if result.context_enough else "failed"
    add_trace(state, "S5.7", "context_quality_agent", status, result.reason)
    return state


def pr_review_agent(state: PRReviewState) -> PRReviewState:
    files = state.get("changed_files", [])
    summary = state["diff_summary"]
    findings: list[Finding] = []

    logic_files = [file for file in files if file.filename.endswith(SOURCE_EXTENSIONS)]
    test_files = [file for file in files if any(hint in file.filename.lower() for hint in TEST_HINTS)]

    if logic_files and not test_files:
        file = logic_files[0]
        findings.append(
            Finding(
                file_path=file.filename,
                line_number=None,
                severity="medium",
                issue="Logic code changed, but no matching test file appears in this PR.",
                suggestion="Add or update tests for the changed behavior before merge.",
                pr_relevance_reason="This finding is tied to a source file modified by the current PR.",
                relation_to_pr="missing_test_for_changed_logic",
                evidence=f"Changed source file: {file.filename}. No test/spec file was found in changed files.",
            )
        )

    if state.get("pr_goal") and logic_files:
        file = logic_files[0]
        findings.append(
            Finding(
                file_path=file.filename,
                line_number=None,
                severity="low",
                issue="PR goal is present; MVP cannot deeply verify all acceptance cases yet.",
                suggestion="In the next phase, compare implementation against explicit acceptance criteria.",
                pr_relevance_reason="Goal-aware mode is enabled for this PR.",
                relation_to_pr="modified_by_pr",
                evidence=f"PR goal: {state['pr_goal']}",
            )
        )

    state["findings"] = findings
    add_trace(
        state,
        "S5.8",
        "pr_review_agent",
        "passed",
        f"Generated {len(findings)} finding(s) for {summary.main_area}",
    )
    return state


def finding_guardrail_node(state: PRReviewState) -> PRReviewState:
    findings = state.get("findings", [])
    changed_files = state.get("changed_files", [])
    state["guardrail_result"] = GuardrailStatus(
        pr_scope_passed=validate_pr_scope(findings, changed_files),
        evidence_passed=validate_evidence(findings),
        hallucination_passed=validate_file_paths(findings, changed_files),
        score_passed=True,
    )
    state["guardrails"] = state["guardrail_result"]

    passed = (
        state["guardrail_result"].pr_scope_passed
        and state["guardrail_result"].evidence_passed
        and state["guardrail_result"].hallucination_passed
    )
    add_trace(
        state,
        "S5.9",
        "finding_guardrail_node",
        "passed" if passed else "failed",
        "Finding guardrails completed",
    )
    return state


def eval_judge_agent(state: PRReviewState) -> PRReviewState:
    state["eval_result"] = run_rule_eval(state.get("findings", []), state["guardrail_result"])
    add_trace(
        state,
        "S5.10",
        "eval_judge_agent",
        "passed" if state["eval_result"].passed else "failed",
        f"Eval score {state['eval_result'].score}",
    )
    return state


def final_scoring_agent(state: PRReviewState) -> PRReviewState:
    findings = state.get("findings", [])
    penalties = {"low": 3, "medium": 8, "high": 18, "critical": 30}
    score = 100 - sum(penalties[finding.severity] for finding in findings)

    if state["risk_summary"].overall_risk == "high":
        score -= 5
    if not state["eval_result"].passed:
        score -= 10

    score = max(0, min(100, score))

    if score >= 90:
        risk_level = "low"
        recommendation = "merge_ready"
    elif score >= 75:
        risk_level = "medium"
        recommendation = "merge_with_minor_fixes"
    elif score >= 60:
        risk_level = "high"
        recommendation = "fix_before_merge"
    else:
        risk_level = "critical"
        recommendation = "do_not_merge"

    state["overall_score"] = score
    state["confidence"] = 75 if state.get("retrieved_context") else 65
    state["risk_level"] = risk_level
    state["recommendation"] = recommendation
    state["score_result"] = {
        "overall_score": score,
        "confidence": state["confidence"],
        "risk_level": risk_level,
        "recommendation": recommendation,
    }

    state["guardrail_result"] = GuardrailStatus(
        pr_scope_passed=state["guardrail_result"].pr_scope_passed,
        evidence_passed=state["guardrail_result"].evidence_passed,
        hallucination_passed=state["guardrail_result"].hallucination_passed,
        score_passed=validate_score(score, state["confidence"]),
    )
    state["guardrails"] = state["guardrail_result"]
    add_trace(state, "S5.11", "final_scoring_agent", "passed", f"Final score {score}")
    return state


def response_builder_node(state: PRReviewState) -> PRReviewState:
    finding_count = len(state.get("findings", []))
    state["final_summary"] = (
        f"{state['diff_summary'].review_mode} review completed for "
        f"{state['diff_summary'].main_area}. Found {finding_count} finding(s)."
    )
    state["final_response"] = {
        "review_mode": "generic",
        "overall_score": 100,
        "confidence": 0,
        "risk_level": "unknown",
        "recommendation": "workflow_skeleton_only",
        "summary": "Workflow skeleton executed successfully.",
        "findings": [],
    }
    add_trace(state, "S5.12", "response_builder_node", "passed", "Final skeleton response built")
    return state


finding_guardrails_node = finding_guardrail_node
final_response_builder_agent = response_builder_node


def _summarize_file(file_path: str) -> FileChangeSummary:
    lower = file_path.lower()

    if lower.endswith((".md", ".rst", ".txt")) or lower.startswith("docs/"):
        change_type = "docs"
        risk = "low"
    elif any(hint in lower for hint in TEST_HINTS):
        change_type = "test"
        risk = "low"
    elif lower.endswith((".toml", ".yaml", ".yml", ".json", ".env.example")):
        change_type = "config"
        risk = "medium"
    elif "requirements" in lower or "package" in lower or "poetry.lock" in lower:
        change_type = "dependency"
        risk = "medium"
    elif lower.endswith(SOURCE_EXTENSIONS):
        change_type = "business_logic"
        risk = "medium"
    else:
        change_type = "unknown"
        risk = "medium"

    return FileChangeSummary(
        file_path=file_path,
        change_type=change_type,
        summary=f"Changed file: {file_path}",
        risk_hint=risk,
    )


def _guess_main_area(paths: list[str]) -> str:
    joined = " ".join(path.lower() for path in paths)
    if "payment" in joined or "coupon" in joined or "discount" in joined:
        return "payment"
    if "auth" in joined or "login" in joined or "token" in joined:
        return "auth"
    if "security" in joined:
        return "security"
    if "test" in joined:
        return "tests"
    return "application"


def _required_review_types(main_change_type: str) -> list[str]:
    if main_change_type == "docs_change":
        return ["docs"]
    if main_change_type == "test_change":
        return ["test_impact"]
    if main_change_type == "config_change":
        return ["configuration", "regression"]
    if main_change_type == "business_logic_change":
        return ["business_logic", "test_impact", "edge_cases"]
    return ["code_quality", "regression"]
