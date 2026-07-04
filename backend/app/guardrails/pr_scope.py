from app.schemas.finding import Finding
from app.schemas.pr import ChangedFile


def validate_pr_scope(findings: list[Finding], changed_files: list[ChangedFile]) -> bool:
    changed_file_names = {file.filename for file in changed_files}
    return all(finding.file_path in changed_file_names for finding in findings)
