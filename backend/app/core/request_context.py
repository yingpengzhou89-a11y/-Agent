from uuid import uuid4

from fastapi import Request


def get_request_id(request: Request) -> str:
    """
    Get the request ID for the current request.

    Prefer request.state.request_id when middleware has already created it.
    Otherwise use X-Request-ID from the request header.
    If neither exists, generate a UUID.
    """
    request_id = getattr(
        request.state,
        "request_id",
        None,
    )

    if request_id:
        return str(request_id)

    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid4())

    request.state.request_id = request_id

    return request_id


def get_client_ip(request: Request) -> str | None:
    if request.client is None:
        return None

    return request.client.host


def get_user_agent(request: Request) -> str | None:
    return request.headers.get("User-Agent")
