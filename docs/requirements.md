# Requirements

## Project Scope

The system reviews only the current pull request diff and directly related repository context.

## Inputs

- GitHub PR URL: required
- PR Goal: optional

## MVP Functional Requirements

1. Parse GitHub PR URL
2. Fetch PR metadata
3. Fetch changed files and diff
4. Summarize PR changes
5. Run PR-focused review
6. Validate findings using guardrails
7. Produce merge readiness percentage
8. Display result in UI
9. Save review history later

## Out of Scope for MVP

- Inline GitHub comments
- Auto patch generation
- CI failure analysis
- GitHub webhook trigger
- Advanced approval dashboard
