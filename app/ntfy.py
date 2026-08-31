"""ntfy push delivery. Transport only — the notifications table is the source of
truth (spec 9). Failure here must never fail the triggering request.

Topic = {prefix}-{org_unit_uuid} (spec 15: non-guessable id, not the public code).
ntfy access-control/auth expected to be enabled; NTFY_TOKEN authorizes publish.
"""

import logging
import uuid

import httpx

from app.config import get_settings

log = logging.getLogger("ntfy")
settings = get_settings()


def topic_for(org_unit_id: uuid.UUID | str) -> str:
    return f"{settings.ntfy_topic_prefix}-{org_unit_id}"


async def publish(org_unit_id: uuid.UUID | str, title: str, body: str) -> None:
    headers = {"Title": title}
    if settings.ntfy_token:
        headers["Authorization"] = f"Bearer {settings.ntfy_token}"
    url = f"{settings.ntfy_url.rstrip('/')}/{topic_for(org_unit_id)}"
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(url, content=body.encode("utf-8"), headers=headers)
    except Exception as e:  # noqa: BLE001 - delivery is best-effort
        log.warning("ntfy publish failed for %s: %s", org_unit_id, e)
