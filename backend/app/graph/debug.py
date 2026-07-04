from app.graph.state import PRReviewState
from app.schemas.trace import TraceStep


def add_trace(state: PRReviewState, step_id: str, agent_id: str, status: str, summary: str) -> None:
    trace = state.setdefault("trace", [])
    trace.append(
        TraceStep(
            request_id=state["request_id"],
            step_id=step_id,
            agent_id=agent_id,
            status=status,
            summary=summary,
        )
    )

    print(f"[{state['request_id']}] [{step_id}] [{agent_id}] {status}: {summary}")
