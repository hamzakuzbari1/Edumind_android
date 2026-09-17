from pydantic import BaseModel, Field

from app.schemas.catalog import CoursePreviewOut


class CheckoutOut(BaseModel):
    items: list[CoursePreviewOut]
    total_amount: float
    currency: str = "SYP"


class DemoCheckoutRequest(BaseModel):
    method: str = Field(pattern="^(card|transfer|wallet|cash)$")


class DemoCheckoutOut(BaseModel):
    ok: bool = True
    payment_id: int
    reference: str
    next_route: str = "/student/payment/success"
    total_amount: float = 0
    currency: str = "SYP"
    unlocked_items: list[CoursePreviewOut] = Field(default_factory=list)
