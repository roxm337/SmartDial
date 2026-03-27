import logging
from typing import Any

import httpx

from app.config import get_settings


logger = logging.getLogger(__name__)


async def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    if not settings.retell_api_key:
        raise ValueError("RETELL_API_KEY is not configured.")

    headers = {
        "Authorization": f"Bearer {settings.retell_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(
        base_url=settings.retell_base_url.rstrip("/"),
        timeout=settings.request_timeout_seconds,
    ) as client:
        try:
            response = await client.post(path, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            logger.exception("Retell transport error for %s", path)
            raise RuntimeError(f"Could not reach Retell API on {path}: {exc}") from exc

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text or str(exc)
        logger.exception("Retell request failed for %s", path)
        raise RuntimeError(f"Retell API error on {path}: {detail}") from exc

    return response.json()


async def _post_without_body(path: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.retell_api_key:
        raise ValueError("RETELL_API_KEY is not configured.")

    headers = {"Authorization": f"Bearer {settings.retell_api_key}"}
    async with httpx.AsyncClient(
        base_url=settings.retell_base_url.rstrip("/"),
        timeout=settings.request_timeout_seconds,
    ) as client:
        try:
            response = await client.post(path, headers=headers)
        except httpx.HTTPError as exc:
            logger.exception("Retell transport error for %s", path)
            raise RuntimeError(f"Could not reach Retell API on {path}: {exc}") from exc

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text or str(exc)
        logger.exception("Retell request failed for %s", path)
        raise RuntimeError(f"Retell API error on {path}: {detail}") from exc

    if not response.content:
        return {}
    return response.json()


async def create_agent(script: str, name: str | None = None) -> dict[str, str]:
    settings = get_settings()

    llm_payload = {
        "model": settings.retell_model,
        "general_prompt": script,
        "general_tools": [
            {
                "type": "end_call",
                "name": "end_call",
                "description": "End the call when the conversation is complete.",
            }
        ],
    }
    llm_response = await _post("/create-retell-llm", llm_payload)

    agent_payload: dict[str, Any] = {
        "response_engine": {
            "type": "retell-llm",
            "llm_id": llm_response["llm_id"],
        },
        "voice_id": settings.retell_voice_id,
        "agent_name": name or "ArteFact Agent",
    }

    if settings.retell_webhook_url:
        agent_payload["webhook_url"] = settings.retell_webhook_url
        agent_payload["webhook_events"] = [
            "call_started",
            "call_ended",
            "call_analyzed",
        ]

    agent_response = await _post("/create-agent", agent_payload)
    await _post_without_body(f"/publish-agent/{agent_response['agent_id']}")

    return {
        "retell_agent_id": agent_response["agent_id"],
        "retell_llm_id": llm_response["llm_id"],
    }


async def start_call(
    retell_agent_id: str,
    phone: str,
    name: str | None,
    metadata: dict[str, str],
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.retell_from_number:
        raise ValueError("RETELL_FROM_NUMBER is not configured.")

    payload = {
        "from_number": settings.retell_from_number,
        "to_number": phone,
        "override_agent_id": retell_agent_id,
        "metadata": metadata,
    }

    if name:
        payload["retell_llm_dynamic_variables"] = {"name": name}

    return await _post("/v2/create-phone-call", payload)
