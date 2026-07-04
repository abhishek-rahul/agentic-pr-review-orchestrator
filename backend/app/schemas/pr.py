from pydantic import BaseModel, Field


class PRReviewRequest(BaseModel):
    pr_url: str = Field(..., min_length=10)
    pr_goal: str | None = None


class PRRef(BaseModel):
    owner: str
    repo: str
    pr_number: int


class PRMetadata(BaseModel):
    title: str
    author: str
    base_branch: str
    head_branch: str
    state: str
    additions: int = 0
    deletions: int = 0
    changed_files_count: int = 0


class ChangedFile(BaseModel):
    filename: str
    status: str
    additions: int = 0
    deletions: int = 0
    patch: str | None = None
