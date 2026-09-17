"""Public language certificate verification."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.language_certificate import CertificateVerifyOut
from app.services.language_certificate_service import verify_certificate

router = APIRouter(tags=["Language Certificates"])


@router.get("/verify-certificate/{certificate_number}", response_model=CertificateVerifyOut)
async def verify_certificate_public(
    certificate_number: str,
    db: AsyncSession = Depends(get_db),
):
    return CertificateVerifyOut(**await verify_certificate(db, certificate_number=certificate_number))
