import enum


class LanguageSkill(str, enum.Enum):
    reading = "reading"
    listening = "listening"
    writing = "writing"
    speaking = "speaking"


class LanguageLevel(str, enum.Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class LanguageOnboardingStep(str, enum.Enum):
    select_language = "select_language"
    placement = "placement"
    dashboard = "dashboard"


class LanguagePlacementAttemptStatus(str, enum.Enum):
    in_progress = "in_progress"
    submitted = "submitted"
    abandoned = "abandoned"


class LanguageContentProgressStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"


class LanguageVocabularyStatus(str, enum.Enum):
    new = "new"
    learning = "learning"
    known = "known"


from app.models.enrollment import PaymentItemProductType  # noqa: F401 — re-export

class OverallLevelMethod(str, enum.Enum):
    bottleneck = "bottleneck"
