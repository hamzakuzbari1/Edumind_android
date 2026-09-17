from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_student_actor
from app.db.session import get_db
from app.models.user import User
from app.schemas.payment import CheckoutOut, DemoCheckoutOut, DemoCheckoutRequest
from app.services import payment_service

router = APIRouter(prefix="/student/payments", tags=["Payments"])


@router.get("/checkout", response_model=CheckoutOut)
async def checkout(
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    return await payment_service.get_checkout(db, student.id)


@router.post("/demo-checkout", response_model=DemoCheckoutOut)
async def demo_checkout(
    body: DemoCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    student: User = Depends(require_student_actor()),
):
    result = await payment_service.demo_checkout(db, student.id, body.method)
    await db.commit()
    return result
