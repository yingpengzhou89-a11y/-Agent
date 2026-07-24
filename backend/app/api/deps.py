from uuid import UUID

from fastapi import Header


async def current_user_id(x_user_id: UUID = Header(alias="X-User-ID")) -> UUID:
    """Temporary local-mode identity boundary; replace with real auth in a later phase."""
    return x_user_id

