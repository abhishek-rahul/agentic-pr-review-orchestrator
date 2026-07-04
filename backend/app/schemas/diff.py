from typing import Literal

from pydantic import BaseModel


class FileChangeSummary(BaseModel):
    file_path: str
    change_type: Literal["business_logic", "test", "model", "config", "docs", "dependency", "unknown"]
    summary: str
    risk_hint: Literal["low", "medium", "high"]


class DiffSummary(BaseModel):
    review_mode: Literal["generic", "goal_aware"]
    main_change_type: Literal[
        "business_logic_change",
        "test_change",
        "config_change",
        "docs_change",
        "dependency_change",
        "mixed_change",
    ]
    main_area: str
    goal_detected: bool
    files: list[FileChangeSummary]
    requires_rag: bool
    required_review_types: list[str]
