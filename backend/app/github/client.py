import httpx

from app.config import get_settings
from app.schemas.pr import ChangedFile, PRMetadata, PRRef

GITHUB_API_BASE = "https://api.github.com"


def github_headers() -> dict[str, str]:
    settings = get_settings()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


async def fetch_pr_metadata(pr: PRRef) -> PRMetadata:
    url = f"{GITHUB_API_BASE}/repos/{pr.owner}/{pr.repo}/pulls/{pr.pr_number}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers=github_headers())
        response.raise_for_status()
        data = response.json()

    return PRMetadata(
        title=data.get("title", ""),
        author=data.get("user", {}).get("login", "unknown"),
        base_branch=data.get("base", {}).get("ref", "unknown"),
        head_branch=data.get("head", {}).get("ref", "unknown"),
        state=data.get("state", "unknown"),
        additions=data.get("additions", 0),
        deletions=data.get("deletions", 0),
        changed_files_count=data.get("changed_files", 0),
    )


async def fetch_changed_files(pr: PRRef) -> list[ChangedFile]:
    url = f"{GITHUB_API_BASE}/repos/{pr.owner}/{pr.repo}/pulls/{pr.pr_number}/files"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers=github_headers())
        response.raise_for_status()
        data = response.json()

    return [
        ChangedFile(
            filename=item.get("filename", ""),
            status=item.get("status", "modified"),
            additions=item.get("additions", 0),
            deletions=item.get("deletions", 0),
            patch=item.get("patch"),
        )
        for item in data
    ]
