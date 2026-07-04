from fastapi import APIRouter, Header, HTTPException
from httpx import HTTPStatusError

from app.schemas.pr import PRReviewRequest
from app.schemas.review import ReviewResult
from app.services.review_service import review_pr

router = APIRouter()


@router.post("/review-pr", response_model=ReviewResult)
async def run_pr_review(
    request: PRReviewRequest,
    x_request_id: str | None = Header(default=None),
) -> ReviewResult:
    try:
        return await review_pr(request.pr_url, request.pr_goal, request_id=x_request_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except HTTPStatusError as error:
        raise HTTPException(
            status_code=error.response.status_code,
            detail="GitHub API request failed. Check PR URL, repo visibility, or GitHub token.",
        ) from error
