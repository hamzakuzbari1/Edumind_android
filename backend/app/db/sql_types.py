"""SQL helpers for schema/ORM mismatches (e.g. VARCHAR columns vs PG enums)."""

from sqlalchemy import String, cast

from app.models.user import User, UserRole


def user_role_equals(role: UserRole | str):
    """Compare users.role when DB stores VARCHAR but ORM uses Python Enum."""
    value = role.value if isinstance(role, UserRole) else role
    return cast(User.role, String) == value
