from pydantic import BaseModel


class FinalResponse(BaseModel):
    summary: str
