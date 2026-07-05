from typing import Any

from app.ai.llm_gateway import get_llm
from app.evals.rule_eval import run_rule_eval
from app.github.client import fetch_changed_files, fetch_pr_metadata
from app.github.parser import parse_pr_url
from app.graph.debug import add_trace
from app.graph.state import PRReviewState
from app.guardrails.evidence import validate_evidence
from app.guardrails.hallucination import validate_file_paths
from app.guardrails.pr_scope import validate_pr_scope
from app.guardrails.scoring import validate_score
from app.rag import retriever as rag_retriever
from app.rag.retriever import retrieve_context_placeholder
from app.schemas.diff import DiffSummary, FileChangeSummary
from app.schemas.eval import GuardrailStatus
from app.schemas.finding import Finding, FindingList
from app.schemas.pr import ChangedFile, PRMetadata
from app.schemas.rag import ContextQualityResult, RAGQuery, RAGQueryPlan, RetrievedContext
from app.schemas.risk import RiskSummary

SOURCE_EXTENSIONS = (".py", ".js", ".ts", ".tsx", ".java", ".go")
TEST_HINTS = ("test", "spec")

# url parse kro 
# todo github token geenrate kro
def parse_pr_url_node(state: PRReviewState) -> PRReviewState:
    pr_ref = parse_pr_url(state["pr_url"])
    state["pr_ref"] = pr_ref
    state["owner"] = pr_ref.owner
    state["repo"] = pr_ref.repo
    state["pr_number"] = pr_ref.pr_number
    add_trace(state, _step_id(state, "S5.1", "S6A.1"), "parse_pr_url_node", "passed", "PR URL parsed")
    return state

# PR ka detail layega
async def fetch_pr_data_node(state: PRReviewState) -> PRReviewState:
    pr_ref = state["pr_ref"]
    if _workflow_mode(state) == "skeleton":
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

    try:
        state["pr_metadata"] = await fetch_pr_metadata(pr_ref)
        state["changed_files"] = await fetch_changed_files(pr_ref)
        state["raw_diff"] = "\n".join(file.patch or "" for file in state["changed_files"])
    except Exception as exc:
        _append_error(state, "S6A.2", "fetch_pr_data_node", str(exc))
        raise RuntimeError(f"Failed to fetch PR data for {state['pr_url']}: {exc}") from exc

    add_trace(
        state,
        "S6A.2",
        "fetch_pr_data_node",
        "passed",
        f"Fetched {len(state['changed_files'])} changed file(s) from GitHub",
    )
    return state


def diff_understanding_agent(state: PRReviewState) -> PRReviewState:
    if _workflow_mode(state) == "live":
        try:
            state["diff_summary"] = _get_structured_llm(DiffSummary).invoke(
                _diff_prompt(state)
            )
        except Exception as exc:
            _append_error(state, "S6A.3", "diff_understanding_agent", str(exc))
            state["diff_summary"] = _deterministic_diff_summary(state)
    else:
        state["diff_summary"] = _deterministic_diff_summary(state)

    add_trace(
        state,
        _step_id(state, "S5.3", "S6A.3"),
        "diff_understanding_agent",
        "passed",
        f"Detected {state['diff_summary'].main_change_type} in {state['diff_summary'].main_area}",
    )
    return state


def risk_classification_agent(state: PRReviewState) -> PRReviewState:
    if _workflow_mode(state) == "live":
        try:
            state["risk_summary"] = _get_structured_llm(RiskSummary).invoke(
                _risk_prompt(state)
            )
        except Exception as exc:
            _append_error(state, "S6A.4", "risk_classification_agent", str(exc))
            state["risk_summary"] = _deterministic_risk_summary(state)
    else:
        state["risk_summary"] = _deterministic_risk_summary(state)

    add_trace(
        state,
        _step_id(state, "S5.4", "S6A.4"),
        "risk_classification_agent",
        "passed",
        f"Risk classified as {state['risk_summary'].overall_risk}",
    )
    return state


def rag_query_planner_agent(state: PRReviewState) -> PRReviewState:
    if _workflow_mode(state) == "live":
        try:
            plan = _get_structured_llm(RAGQueryPlan).invoke(_rag_query_prompt(state))
        except Exception as exc:
            _append_error(state, "S6A.5", "rag_query_planner_agent", str(exc))
            plan = _fallback_rag_query_plan(state)

        state["rag_query_plan"] = _clean_rag_query_plan(plan, state)
        previous_queries = state.setdefault("previous_rag_queries", [])
        for item in state["rag_query_plan"].queries:
            if item.query not in previous_queries:
                previous_queries.append(item.query)
        print(
            "[rag_query_planner_agent] "
            f"queries={len(state['rag_query_plan'].queries)} top_k={state['rag_query_plan'].top_k}"
        )
        add_trace(
            state,
            "S6A.5",
            "rag_query_planner_agent",
            "passed",
            f"Planned {len(state['rag_query_plan'].queries)} RAG query(ies)",
        )
        return state

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
    if _workflow_mode(state) == "live":
        plan = state.get("rag_query_plan")
        if not plan or not plan.queries:
            state["retrieved_context"] = []
            add_trace(state, "S6A.6", "rag_retriever_node", "skipped", "No RAG queries to execute")
            return state

        contexts: list[RetrievedContext] = []
        try:
            for item in plan.queries:
                contexts.extend(
                    rag_retriever.retrieve_context(
                        item.query,
                        repo_name=state["repo"],
                        branch=state["pr_metadata"].base_branch,
                        top_k=plan.top_k,
                    )
                )
        except Exception as exc:
            _append_error(state, "S6A.6", "rag_retriever_node", str(exc))
            contexts = []

        state["retrieved_context"] = _dedupe_and_filter_contexts(contexts)[:10]
        print(
            "[rag_retriever_node] "
            f"queries={len(plan.queries)} chunks_found={len(state['retrieved_context'])}"
        )
        add_trace(
            state,
            "S6A.6",
            "rag_retriever_node",
            "passed",
            f"Retrieved {len(state['retrieved_context'])} context chunk(s)",
        )
        return state

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
    if _workflow_mode(state) == "live":
        basic_result = _basic_context_check(state)
        try:
            state["context_quality"] = _get_structured_llm(ContextQualityResult).invoke(
                _context_quality_prompt(state, basic_result)
            )
        except Exception as exc:
            _append_error(state, "S6A.7", "context_quality_agent", str(exc))
            state["context_quality"] = basic_result

        print(
            "[context_quality_agent] "
            f"enough={state['context_quality'].context_enough} "
            f"retry_count={state.get('retry_count', {}).get('context_quality', 0)}"
        )
        add_trace(
            state,
            "S6A.7",
            "context_quality_agent",
            "passed" if state["context_quality"].context_enough else "failed",
            state["context_quality"].reason,
        )
        return state

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
    if _workflow_mode(state) == "live":
        try:
            state["findings"] = _get_structured_llm(FindingList).invoke(
                _review_prompt(state)
            ).findings
        except Exception as exc:
            _append_error(state, "S6A.8", "pr_review_agent", str(exc))
            state["findings"] = _fallback_findings(state)

        add_trace(
            state,
            "S6A.8",
            "pr_review_agent",
            "passed",
            f"Generated {len(state['findings'])} finding(s) for {state['diff_summary'].main_area}",
        )
        return state

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
        _step_id(state, "S5.9", "S6A.9"),
        "finding_guardrail_node",
        "passed" if passed else "failed",
        "Finding guardrails completed",
    )
    return state


def eval_judge_agent(state: PRReviewState) -> PRReviewState:
    state["eval_result"] = run_rule_eval(state.get("findings", []), state["guardrail_result"])
    add_trace(
        state,
        _step_id(state, "S5.10", "S6A.10"),
        "eval_judge_agent",
        "passed" if state["eval_result"].passed else "failed",
        f"Eval score {state['eval_result'].score}",
    )
    return state


def final_scoring_agent(state: PRReviewState) -> PRReviewState:
    findings = state.get("findings", [])
    if _workflow_mode(state) == "live":
        base_by_risk = {"low": 95, "medium": 82, "high": 65, "critical": 50}
        penalties = {"low": 5, "medium": 12, "high": 25, "critical": 35}
        score = base_by_risk.get(state["risk_summary"].overall_risk, 60)
        score -= sum(penalties[finding.severity] for finding in findings)
        if not (
            state["guardrail_result"].pr_scope_passed
            and state["guardrail_result"].evidence_passed
            and state["guardrail_result"].hallucination_passed
        ):
            score = min(score, 60)
    else:
        penalties = {"low": 3, "medium": 8, "high": 18, "critical": 30}
        score = 100 - sum(penalties[finding.severity] for finding in findings)
        if state["risk_summary"].overall_risk == "high":
            score -= 5
        if not state["eval_result"].passed:
            score -= 10

    score = max(0, min(100, score))

    if _workflow_mode(state) == "live":
        if score >= 85 and not any(finding.severity in {"high", "critical"} for finding in findings):
            risk_level = state["risk_summary"].overall_risk
            recommendation = "merge_ready"
        elif score >= 70:
            risk_level = state["risk_summary"].overall_risk
            recommendation = "merge_with_caution"
        elif score >= 40:
            risk_level = state["risk_summary"].overall_risk
            recommendation = "fix_before_merge"
        else:
            risk_level = state["risk_summary"].overall_risk
            recommendation = "needs_human_review"
    elif score >= 90:
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
    state["confidence"] = 75 if _workflow_mode(state) == "live" and not state.get("errors") else 60
    if _workflow_mode(state) == "skeleton":
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
    add_trace(state, _step_id(state, "S5.11", "S6A.11"), "final_scoring_agent", "passed", f"Final score {score}")
    return state


def response_builder_node(state: PRReviewState) -> PRReviewState:
    if _workflow_mode(state) == "live":
        state["final_summary"] = _build_live_summary(state)
        add_trace(state, "S6A.12", "response_builder_node", "passed", "Final live response built")
        state["final_response"] = {
            "request_id": state["request_id"],
            "pr_url": state["pr_url"],
            "review_mode": state["diff_summary"].review_mode,
            "overall_score": state["score_result"]["overall_score"],
            "confidence": state["score_result"]["confidence"],
            "risk_level": state["score_result"]["risk_level"],
            "recommendation": state["score_result"]["recommendation"],
            "summary": state["final_summary"],
            "findings": [_finding_to_response(finding) for finding in state.get("findings", [])],
            "trace": [_model_dump(item) for item in state.get("trace", [])],
            "errors": state.get("errors", []),
        }
        return state

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


def _workflow_mode(state: PRReviewState) -> str:
    return state.get("workflow_mode") or "live"


def _step_id(state: PRReviewState, skeleton_id: str, live_id: str) -> str:
    if _workflow_mode(state) == "skeleton":
        return skeleton_id
    return live_id


def _append_error(state: PRReviewState, step_id: str, agent_id: str, message: str) -> None:
    state.setdefault("errors", []).append(
        {
            "step_id": step_id,
            "agent_id": agent_id,
            "message": message,
        }
    )


def _get_structured_llm(schema: type[Any]):
    return get_llm().with_structured_output(schema)


def _trim_diff(raw_diff: str, max_chars: int = 12000) -> str:
    if len(raw_diff) <= max_chars:
        return raw_diff
    return raw_diff[:max_chars] + "\n...[diff trimmed for Step 6A]..."


def _model_dump(value) -> dict:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return dict(value)


def _deterministic_diff_summary(state: PRReviewState) -> DiffSummary:
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

    return DiffSummary(
        review_mode="goal_aware" if state.get("pr_goal") else "generic",
        main_change_type=main_change_type,
        main_area=main_area,
        goal_detected=bool(state.get("pr_goal")),
        files=file_summaries,
        requires_rag=not has_docs,
        required_review_types=_required_review_types(main_change_type),
    )


def _deterministic_risk_summary(state: PRReviewState) -> RiskSummary:
    summary = state["diff_summary"]
    raw_diff = state.get("raw_diff", "").lower()

    if "validation" in raw_diff and any(line.startswith("-") for line in raw_diff.splitlines()):
        risk = "high"
        reasons = ["Validation logic appears to be removed or changed"]
    elif summary.main_change_type == "docs_change":
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

    return RiskSummary(
        overall_risk=risk,
        risk_reasons=reasons,
        required_review_types=summary.required_review_types,
    )


def _fallback_rag_query_plan(state: PRReviewState) -> RAGQueryPlan:
    summary = state["diff_summary"]
    risk = state["risk_summary"]
    changed_paths = " ".join(file.filename for file in state.get("changed_files", []))
    query_texts = [
        f"{summary.main_area} related source code {changed_paths}".strip(),
        f"{summary.main_area} related tests validation edge cases".strip(),
    ]
    if state.get("pr_goal"):
        query_texts.append(str(state["pr_goal"]))
    for reason in risk.risk_reasons[:2]:
        query_texts.append(f"{summary.main_area} {reason}")

    return RAGQueryPlan(
        queries=[
            RAGQuery(query=query, purpose="Find PR-related repository context")
            for query in query_texts
            if query.strip()
        ],
        top_k=6,
    )


def _clean_rag_query_plan(plan: RAGQueryPlan, state: PRReviewState) -> RAGQueryPlan:
    previous = set(state.get("previous_rag_queries", []))
    cleaned: list[RAGQuery] = []
    for item in plan.queries:
        query = item.query.strip()
        if not query or query in previous or _is_generic_query(query):
            continue
        cleaned.append(RAGQuery(query=query, purpose=item.purpose.strip() or "Find PR-related context"))
        if len(cleaned) == 5:
            break

    if not cleaned:
        return _fallback_rag_query_plan(state)

    top_k = plan.top_k or 6
    return RAGQueryPlan(queries=cleaned, top_k=max(1, min(top_k, 10)))


def _is_generic_query(query: str) -> bool:
    lower = query.lower().strip()
    generic_phrases = {
        "best practices",
        "clean code",
        "security tips",
        "general review",
        "how to write good tests",
    }
    return lower in generic_phrases or any(phrase == lower for phrase in generic_phrases)


def _dedupe_and_filter_contexts(contexts: list[RetrievedContext]) -> list[RetrievedContext]:
    seen: set[str] = set()
    filtered: list[RetrievedContext] = []
    for context in contexts:
        if _is_unsafe_context_path(context.file_path):
            continue
        key = f"{context.file_path}:{context.content[:120]}"
        if key in seen:
            continue
        seen.add(key)
        filtered.append(context)
    return filtered


def _is_unsafe_context_path(file_path: str) -> bool:
    lower = file_path.lower().replace("\\", "/")
    blocked_parts = [
        ".env",
        ".git/",
        ".venv/",
        "node_modules/",
        "dist/",
        "build/",
        "__pycache__/",
    ]
    return (
        any(part in lower for part in blocked_parts)
        or lower.endswith((".log", ".pyc", ".class", ".jar", ".png", ".jpg", ".jpeg", ".gif"))
    )


def _basic_context_check(state: PRReviewState) -> ContextQualityResult:
    summary = state["diff_summary"]
    risk = state["risk_summary"]
    contexts = state.get("retrieved_context", [])

    if summary.main_change_type in {"docs_change", "test_change"}:
        return ContextQualityResult(
            context_enough=True,
            reason="Weak or empty context is acceptable for docs/test-only PR.",
            missing_context=[],
            suggested_queries=[],
        )

    if contexts:
        return ContextQualityResult(
            context_enough=True,
            reason="Retrieved repository context is available for the PR review.",
            missing_context=[],
            suggested_queries=[],
        )

    if summary.main_change_type == "business_logic_change":
        suggested = [
            f"{summary.main_area} related source code",
            f"{summary.main_area} related tests",
        ]
        if risk.overall_risk in {"high", "critical"}:
            suggested.append(f"{summary.main_area} validation rules")
        return ContextQualityResult(
            context_enough=False,
            reason="No context retrieved for business logic PR.",
            missing_context=["related source code", "related tests"],
            suggested_queries=suggested,
        )

    return ContextQualityResult(
        context_enough=True,
        reason="Context is acceptable for this basic Step 6B review.",
        missing_context=[],
        suggested_queries=[],
    )


def _fallback_findings(state: PRReviewState) -> list[Finding]:
    files = state.get("changed_files", [])
    raw_diff = state.get("raw_diff", "").lower()
    findings: list[Finding] = []
    logic_files = [file for file in files if file.filename.endswith(SOURCE_EXTENSIONS)]
    test_files = [file for file in files if any(hint in file.filename.lower() for hint in TEST_HINTS)]

    if "validation" in raw_diff and any(line.startswith("-") for line in raw_diff.splitlines()) and logic_files:
        file = logic_files[0]
        findings.append(
            Finding(
                file_path=file.filename,
                line_number=None,
                severity="high",
                issue="Validation logic appears to be removed or weakened in this PR.",
                suggestion="Verify the validation behavior and add focused regression tests.",
                pr_relevance_reason="The finding is based on removed validation text in the PR diff.",
                relation_to_pr="introduced_by_pr",
                evidence="The PR diff contains removed validation-related lines.",
            )
        )
    elif logic_files and not test_files:
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

    return findings


def _diff_prompt(state: PRReviewState) -> str:
    metadata = state.get("pr_metadata")
    changed_files = ", ".join(file.filename for file in state.get("changed_files", []))
    title = metadata.title if metadata else ""
    return (
        "Summarize this GitHub PR as structured DiffSummary. Review only changed files.\n"
        "Allowed main_change_type values: business_logic_change, test_change, config_change, "
        "docs_change, dependency_change, mixed_change.\n"
        "Allowed file change_type values: business_logic, test, model, config, docs, "
        "dependency, unknown.\n"
        f"PR title: {title}\n"
        f"PR goal: {state.get('pr_goal') or ''}\n"
        f"Changed files: {changed_files}\n"
        f"Diff:\n{_trim_diff(state.get('raw_diff', ''))}"
    )


def _rag_query_prompt(state: PRReviewState) -> str:
    context_quality = state.get("context_quality")
    return (
        "Create a focused RAGQueryPlan for finding repository context relevant to this PR only.\n"
        "Generate 2 to 5 concrete queries. Avoid generic queries such as best practices, "
        "clean code, security tips, general review, or how to write good tests.\n"
        f"PR goal: {state.get('pr_goal') or ''}\n"
        f"Changed files: {[file.filename for file in state.get('changed_files', [])]}\n"
        f"Diff summary: {state['diff_summary'].model_dump()}\n"
        f"Risk summary: {state['risk_summary'].model_dump()}\n"
        f"Previous RAG queries: {state.get('previous_rag_queries', [])}\n"
        f"Missing context: {context_quality.missing_context if context_quality else []}\n"
        f"Suggested queries: {context_quality.suggested_queries if context_quality else []}"
    )


def _risk_prompt(state: PRReviewState) -> str:
    return (
        "Classify PR risk as structured RiskSummary. Focus on current PR changes only.\n"
        "Allowed overall_risk values: low, medium, high, critical.\n"
        f"Diff summary: {state['diff_summary'].model_dump()}\n"
        f"Changed files: {[file.filename for file in state.get('changed_files', [])]}\n"
        f"Diff:\n{_trim_diff(state.get('raw_diff', ''))}"
    )


def _review_prompt(state: PRReviewState) -> str:
    return (
        "Generate a small list of PR review findings as structured FindingList.\n"
        "Rules: review only current PR diff, do not invent file paths, do not invent line numbers, "
        "docs-only/test-only PRs usually have no findings, business logic without tests can be a finding, "
        "removed validation visible in the diff should be high risk.\n"
        "Retrieved repo context is provided only to understand the current PR. Do not report issues "
        "from context files unless the current PR introduced, modified, or made worse the issue.\n"
        "Allowed severity values: low, medium, high, critical.\n"
        "Allowed relation_to_pr values: introduced_by_pr, modified_by_pr, made_worse_by_pr, "
        "missing_test_for_changed_logic, regression_risk.\n"
        f"PR metadata: {state['pr_metadata'].model_dump()}\n"
        f"Changed files: {[file.model_dump() for file in state.get('changed_files', [])]}\n"
        f"Diff summary: {state['diff_summary'].model_dump()}\n"
        f"Risk summary: {state['risk_summary'].model_dump()}\n"
        f"Context quality: {state.get('context_quality').model_dump() if state.get('context_quality') else {}}\n"
        f"Retrieved context: {[_context_for_prompt(item) for item in state.get('retrieved_context', [])]}\n"
        f"PR goal: {state.get('pr_goal') or ''}\n"
        f"Diff:\n{_trim_diff(state.get('raw_diff', ''))}"
    )


def _context_quality_prompt(state: PRReviewState, basic_result: ContextQualityResult) -> str:
    return (
        "Decide whether retrieved repository context is enough for this PR review as "
        "structured ContextQualityResult.\n"
        "Docs-only and test-only PRs can pass with weak context. Business logic, payment, auth, "
        "security, high-risk, or critical PRs should prefer related source and test context.\n"
        f"Basic check result: {basic_result.model_dump()}\n"
        f"PR goal: {state.get('pr_goal') or ''}\n"
        f"Changed files: {[file.filename for file in state.get('changed_files', [])]}\n"
        f"Diff summary: {state['diff_summary'].model_dump()}\n"
        f"Risk summary: {state['risk_summary'].model_dump()}\n"
        f"RAG query plan: {state.get('rag_query_plan').model_dump() if state.get('rag_query_plan') else {}}\n"
        f"Retrieved context: {[_context_for_prompt(item) for item in state.get('retrieved_context', [])]}"
    )


def _context_for_prompt(context: RetrievedContext) -> dict:
    return {
        "file_path": context.file_path,
        "reason": context.reason,
        "score": context.score,
        "content_preview": context.content[:600],
    }


def _build_live_summary(state: PRReviewState) -> str:
    finding_count = len(state.get("findings", []))
    return (
        f"{state['diff_summary'].review_mode} review completed for "
        f"{state['diff_summary'].main_area}. Found {finding_count} finding(s)."
    )


def _finding_to_response(finding: Finding) -> dict:
    return {
        "title": finding.issue,
        "severity": finding.severity,
        "file_path": finding.file_path,
        "line_number": finding.line_number,
        "evidence": finding.evidence,
        "recommendation": finding.suggestion,
        "why_it_matters": finding.pr_relevance_reason,
        "relation_to_pr": finding.relation_to_pr,
    }
