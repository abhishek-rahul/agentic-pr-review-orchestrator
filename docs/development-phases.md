# Development Plan

## Step 1: Sample repo select/prepare

Choose a small but realistic repo with business logic and tests.

Manual/Codex: Mostly manual, Codex can help create sample repo code.

## Step 2: LLM Gateway + Embedding Gateway

Create provider abstraction for LLM and embeddings.

Manual/Codex: Codex implementation, manual review.

## Step 3: Repo context indexing into Elasticsearch

Load useful repo files, split into chunks, create embeddings, store in Elasticsearch.

Manual/Codex: Codex implementation, manual decisions for file filters and chunking.

## Step 4: Sample PRs create for testing

Create docs-only, business logic, missing test, good PR, and config/dependency PRs.

Manual/Codex: Manual scenario design, Codex can create code changes.

## Step 5: LangGraph workflow skeleton without UI/API

Run workflow from a local script before API and UI.

Manual/Codex: Codex scaffold, manual architecture review.

## Step 6: Agents + tool nodes + guardrails + eval one by one

Implementation order:

```text
6.1 Parse PR URL Node
6.2 Fetch PR Data Node
6.3 Diff Understanding Agent + Diff Summary Schema Guardrail
6.4 Risk Classification Agent + Risk Summary Schema Guardrail
6.5 RAG Query Planner Agent + RAG Query Guardrail
6.6 RAG Retriever Node + Retrieval Validation
6.7 Context Quality Agent + Context Retry Loop
6.8 PR Review Agent
6.9 Finding Guardrails
6.10 Eval Judge Agent + Eval Retry Loop
6.11 Final Scoring Agent + Score Guardrail
6.12 Final Response Builder Agent + Response Schema Validation
```

Manual/Codex: Codex implementation, manual prompt/schema/rule review.

## Step 7: Clear debug logging

Keep logs readable. Do not log secrets or huge diffs.

Manual/Codex: Codex implementation, manual format decision.

## Step 8: FastAPI integration

Expose workflow through API after local workflow is stable.

Manual/Codex: Codex implementation.

## Step 9: React UI integration

Create UI for PR URL, optional goal, score, findings, guardrails, and debug trace.

Manual/Codex: Codex scaffold, manual UX review.

## Step 10: PostgreSQL persistence

Save structured review results, not every debug log.

Manual/Codex: Codex implementation, manual schema review.

## Later

- Human approval + GitHub comment posting
- CI analysis
- Auto patch suggestion
- Webhook trigger
- Incremental repo indexing
