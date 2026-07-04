from app.schemas.finding import Finding


def validate_evidence(findings: list[Finding]) -> bool:
    return all(bool(finding.evidence.strip()) for finding in findings)
