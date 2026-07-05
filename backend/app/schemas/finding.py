from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]
PRRelation = Literal[
    "introduced_by_pr",
    "modified_by_pr",
    "made_worse_by_pr",
    "missing_test_for_changed_logic",
    "regression_risk",
]


class Finding(BaseModel):
    file_path: str
    line_number: int | None = None
    severity: Severity
    issue: str
    suggestion: str
    pr_relevance_reason: str
    relation_to_pr: PRRelation
    evidence: str = Field(..., min_length=3)


class FindingList(BaseModel):
    findings: list[Finding]
