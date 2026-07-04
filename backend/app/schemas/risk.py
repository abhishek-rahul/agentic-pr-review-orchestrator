from typing import Literal

from pydantic import BaseModel


class RiskSummary(BaseModel):
    overall_risk: Literal["low", "medium", "high", "critical"]
    risk_reasons: list[str]
    required_review_types: list[str]
