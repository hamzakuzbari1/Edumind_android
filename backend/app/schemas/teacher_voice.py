from pydantic import BaseModel, Field


class TeacherVoiceSampleOut(BaseModel):
    has_sample: bool
    id: int | None = None
    processing_status: str | None = None
    status_label: str | None = None
    duration_seconds: float | None = None
    uploaded_at: str | None = None
    error_message: str | None = None
    requires_verification: bool = False
    ready: bool = False


class TeacherVoiceSampleItemOut(BaseModel):
    id: int
    processing_status: str
    status_label: str
    duration_seconds: float | None = None
    uploaded_at: str | None = None
    error_message: str | None = None
    requires_verification: bool = False
    ready: bool = False
    is_latest_ready: bool = False


class TeacherVoiceProfileOut(BaseModel):
    has_ready_profile: bool = False
    latest_ready_id: int | None = None
    samples: list[TeacherVoiceSampleItemOut] = Field(default_factory=list)


class VoicePreviewIn(BaseModel):
    text: str = "مرحباً، أنا معلمك الذكي. سأشرح لك الدرس بأسلوبي المعتاد."


class VoicePreviewOut(BaseModel):
    audio_url: str | None = None
    message: str
