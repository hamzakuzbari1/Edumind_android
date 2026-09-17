from pydantic import BaseModel, Field


class LinkedParentOut(BaseModel):
    parent_id: int
    display_name: str
    relationship_label: str
    linked_at: str | None = None
    last_viewed_at: str | None = None
    is_active: bool = True


class LinkedParentsSummaryOut(BaseModel):
    total_linked: int = 0
    active_linked: int = 0


class StudentLinkedParentsOut(BaseModel):
    parents: list[LinkedParentOut] = Field(default_factory=list)
    summary: LinkedParentsSummaryOut = Field(default_factory=LinkedParentsSummaryOut)
