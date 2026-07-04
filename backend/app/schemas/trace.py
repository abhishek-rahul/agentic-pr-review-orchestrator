from pydantic import BaseModel


class TraceStep(BaseModel):
    request_id: str
    step_id: str
    agent_id: str
    status: str
    summary: str
