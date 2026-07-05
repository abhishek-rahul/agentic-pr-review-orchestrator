import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.graph.workflow import build_review_graph


def _initial_state(pr_url: str, pr_goal: str | None, workflow_mode: str) -> dict:
    return {
        "request_id": f"req_{uuid.uuid4().hex[:12]}",
        "workflow_mode": workflow_mode,
        "pr_url": pr_url,
        "pr_goal": pr_goal,
        "retry_count": {
            "context_quality": 0,
            "finding_guardrail": 0,
            "eval_judge": 0,
            "scoring": 0,
        },
        "errors": [],
        "trace": [],
    }


async def _run(pr_url: str, pr_goal: str | None, workflow_mode: str) -> dict:
    graph = build_review_graph()
    return await graph.ainvoke(_initial_state(pr_url, pr_goal, workflow_mode))


def _trace_item_to_dict(item) -> dict:
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return dict(item)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PR review workflow locally.")
    parser.add_argument("--pr-url", required=True)
    parser.add_argument("--pr-goal", default=None)
    parser.add_argument("--workflow-mode", choices=["skeleton", "live"], default="skeleton")
    args = parser.parse_args()

    result = asyncio.run(_run(args.pr_url, args.pr_goal, args.workflow_mode))

    print("final_response:")
    print(json.dumps(result["final_response"], indent=2))
    print()
    print("trace:")
    for item in result.get("trace", []):
        trace = _trace_item_to_dict(item)
        print(
            f"{trace['step_id']} | {trace['agent_id']} | "
            f"{trace['status']} | {trace['summary']}"
        )


if __name__ == "__main__":
    main()
