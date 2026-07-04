import re

from app.schemas.pr import PRRef

PR_URL_PATTERN = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)/?$"
)


def parse_pr_url(pr_url: str) -> PRRef:
    match = PR_URL_PATTERN.match(pr_url.strip())
    if not match:
        raise ValueError("Invalid GitHub PR URL. Expected https://github.com/{owner}/{repo}/pull/{number}")

    return PRRef(
        owner=match.group("owner"),
        repo=match.group("repo"),
        pr_number=int(match.group("number")),
    )
