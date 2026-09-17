"""Client metadata from HTTP request."""

from fastapi import Request


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")
