from datetime import datetime



from pydantic import BaseModel, Field





class AchievementOut(BaseModel):

    achievement_key: str

    icon: str = ""

    title: str

    description: str = ""

    unlocked_at: datetime | str | None = None





class BadgeOut(BaseModel):

    achievement_key: str

    icon: str = ""

    title: str

    description: str = ""

    unlocked: bool = False

    unlocked_at: datetime | str | None = None





class XpRuleOut(BaseModel):

    category: str = ""

    label: str

    xp: int





class XpActivityOut(BaseModel):

    label: str

    xp: int = 0

    occurred_at: datetime | str | None = None

    kind: str = "xp"





class GamificationProfileOut(BaseModel):

    level: int = 1

    total_xp: int = 0

    xp_to_next_level: int = 0

    xp_in_level: int = 0

    xp_for_level: int = 0

    progress_percent: int = 0

    is_max_level: bool = False

    current_streak: int = 0

    longest_streak: int = 0

    streak_display: str = ""

    achievements: list[AchievementOut] = Field(default_factory=list)

    achievement_count: int = 0

    badges: list[BadgeOut] = Field(default_factory=list)

    xp_rules: list[XpRuleOut] = Field(default_factory=list)

    recent_activity: list[XpActivityOut] = Field(default_factory=list)
