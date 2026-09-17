from datetime import datetime

from pydantic import BaseModel


class ActivityEventOut(BaseModel):
    id: int
    event_type: str
    title: str
    description: str | None = None
    payload: dict | None = None
    created_at: datetime
    relative_time: str = ""

    model_config = {"from_attributes": True}


class ParentInsightOut(BaseModel):
    id: str
    text: str
    severity: str = "info"
    icon: str = "mdi-lightbulb-on"
    evidence: list[str] = []
    data_source: str | None = None
