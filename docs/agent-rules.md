# Agent Rules

## Common rules for all AI nodes

- No raw LLM text should be stored directly in LangGraph state.
- Use structured output schemas.
- Keep prompts focused and short.
- Use only current PR diff plus directly related repo context.
- Do not perform full repo audit.
- Do not invent files, line numbers, functions, or tests.

## Diff Understanding Agent

Purpose: summarize what changed. Do not generate review findings here.

Output: DiffSummary.

## Risk Classification Agent

Purpose: classify PR risk and required review types.

Output: RiskSummary.

## RAG Query Planner Agent

Purpose: create focused queries for repo context retrieval.

Output: RAGQueryPlan.

## Context Quality Agent

Purpose: decide if retrieved context is enough.

Output: ContextQualityResult.

## PR Review Agent

Purpose: generate PR-related findings only.

Output: FindingList/list[Finding].

Required per finding:
- file_path
- severity
- issue
- suggestion
- pr_relevance_reason
- relation_to_pr
- evidence

## Eval Judge Agent

Purpose: judge usefulness and PR relevance of findings.

Output: EvalResult.

## Final Scoring Agent

Purpose: produce merge readiness score, confidence, risk, and recommendation.

Score must be 0-100.

## Final Response Builder Agent

Purpose: build UI-friendly final summary. It must not change score or findings.
