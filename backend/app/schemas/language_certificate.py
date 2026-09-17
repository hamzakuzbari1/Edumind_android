from datetime import datetime

from pydantic import BaseModel, Field


class LanguageCertificateItemOut(BaseModel):
    id: int
    certificate_level: str
    certificate_number: str
    verification_code: str
    certificate_status: str
    verification_url: str | None = None
    issued_at: datetime
    pdf_url: str | None = None


class LanguageCertificateEligibilityOut(BaseModel):
    level: str
    eligible: bool
    issued: bool


class LanguageCertificateListOut(BaseModel):
    certificates: list[LanguageCertificateItemOut] = Field(default_factory=list)
    eligibility: list[LanguageCertificateEligibilityOut] = Field(default_factory=list)


class CertificateVerifyOut(BaseModel):
    valid: bool
    student_name: str | None = None
    certificate_level: str | None = None
    issued_at: datetime | None = None
    certificate_number: str | None = None


class LanguageCertificateSummaryOut(BaseModel):
    certificate_level: str
    certificate_number: str
    issued_at: datetime
    verification_url: str | None = None
    pdf_url: str | None = None
