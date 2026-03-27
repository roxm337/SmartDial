import logging
from typing import Any

from app.config import get_settings
from app.db import fetch_all, fetch_one, get_connection
from app.services.retell import start_call


logger = logging.getLogger(__name__)

TERMINAL_CALL_STATUSES = {"ended", "error", "not_connected", "failed", "canceled"}


def list_agents() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT id, name, script, retell_agent_id, retell_llm_id, created_at
        FROM agents
        ORDER BY created_at DESC, id DESC
        """
    )


def list_campaigns() -> list[dict[str, Any]]:
    campaigns = fetch_all(
        """
        SELECT
            campaigns.id,
            campaigns.agent_id,
            campaigns.status,
            campaigns.created_at,
            COUNT(calls.id) AS total_calls,
            SUM(CASE WHEN calls.status IN ('ended', 'error', 'not_connected', 'failed', 'canceled') THEN 1 ELSE 0 END) AS completed_calls
        FROM campaigns
        LEFT JOIN calls ON calls.campaign_id = campaigns.id
        GROUP BY campaigns.id
        ORDER BY campaigns.created_at DESC, campaigns.id DESC
        """
    )
    for campaign in campaigns:
        campaign["completed_calls"] = campaign["completed_calls"] or 0
    return campaigns


def list_calls() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            id,
            campaign_id,
            retell_call_id,
            phone,
            name,
            status,
            transcript,
            duration,
            recording_url,
            created_at,
            updated_at
        FROM calls
        ORDER BY created_at DESC, id DESC
        """
    )


async def create_campaign(agent_id: int, leads: list[dict[str, str | None]]) -> dict[str, Any]:
    settings = get_settings()
    if not settings.retell_api_key:
        raise ValueError("RETELL_API_KEY is not configured.")
    if not settings.retell_from_number:
        raise ValueError("RETELL_FROM_NUMBER is not configured.")

    agent = fetch_one(
        """
        SELECT id, retell_agent_id
        FROM agents
        WHERE id = ?
        """,
        (agent_id,),
    )
    if not agent:
        raise ValueError(f"Agent {agent_id} does not exist.")

    with get_connection() as connection:
        campaign_cursor = connection.execute(
            """
            INSERT INTO campaigns (agent_id, status)
            VALUES (?, ?)
            """,
            (agent_id, "processing"),
        )
        campaign_id = int(campaign_cursor.lastrowid)

        calls: list[dict[str, Any]] = []
        for lead in leads:
            call_cursor = connection.execute(
                """
                INSERT INTO calls (campaign_id, phone, name, status)
                VALUES (?, ?, ?, ?)
                """,
                (campaign_id, lead["phone"], lead.get("name"), "queued"),
            )
            calls.append(
                {
                    "id": int(call_cursor.lastrowid),
                    "phone": lead["phone"],
                    "name": lead.get("name"),
                }
            )

    for call in calls:
        try:
            call_response = await start_call(
                retell_agent_id=agent["retell_agent_id"],
                phone=call["phone"],
                name=call["name"],
                metadata={
                    "campaign_id": str(campaign_id),
                    "call_id": str(call["id"]),
                    "name": call["name"] or "",
                },
            )
            with get_connection() as connection:
                connection.execute(
                    """
                    UPDATE calls
                    SET retell_call_id = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        call_response.get("call_id"),
                        call_response.get("call_status", "registered"),
                        call["id"],
                    ),
                )
        except Exception as exc:
            logger.exception("Failed to start call %s", call["id"])
            with get_connection() as connection:
                connection.execute(
                    """
                    UPDATE calls
                    SET status = ?, transcript = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    ("error", str(exc), call["id"]),
                )

    refresh_campaign_status(campaign_id)
    return get_campaign_detail(campaign_id)


def get_campaign_detail(campaign_id: int) -> dict[str, Any]:
    campaign = fetch_one(
        """
        SELECT
            campaigns.id,
            campaigns.agent_id,
            campaigns.status,
            campaigns.created_at,
            COUNT(calls.id) AS total_calls,
            SUM(CASE WHEN calls.status IN ('ended', 'error', 'not_connected', 'failed', 'canceled') THEN 1 ELSE 0 END) AS completed_calls
        FROM campaigns
        LEFT JOIN calls ON calls.campaign_id = campaigns.id
        WHERE campaigns.id = ?
        GROUP BY campaigns.id
        """,
        (campaign_id,),
    )
    if not campaign:
        raise ValueError(f"Campaign {campaign_id} does not exist.")

    campaign["completed_calls"] = campaign["completed_calls"] or 0
    campaign["calls"] = fetch_all(
        """
        SELECT
            id,
            campaign_id,
            retell_call_id,
            phone,
            name,
            status,
            transcript,
            duration,
            recording_url,
            created_at,
            updated_at
        FROM calls
        WHERE campaign_id = ?
        ORDER BY id ASC
        """,
        (campaign_id,),
    )
    return campaign


def update_call_from_webhook(event: str, call_data: dict[str, Any]) -> dict[str, Any]:
    call_id = call_data.get("call_id")
    metadata = call_data.get("metadata") or {}
    local_call_id = metadata.get("call_id")

    if not call_id and not local_call_id:
        raise ValueError("Webhook payload is missing both call.call_id and metadata.call_id.")

    duration = None
    if call_data.get("duration_ms") is not None:
        duration = int(call_data["duration_ms"] / 1000)
    elif call_data.get("duration") is not None:
        duration = int(call_data["duration"])

    with get_connection() as connection:
        target = None
        if call_id:
            target = connection.execute(
                """
                SELECT id, campaign_id
                FROM calls
                WHERE retell_call_id = ?
                """,
                (call_id,),
            ).fetchone()

        if not target and local_call_id:
            target = connection.execute(
                """
                SELECT id, campaign_id
                FROM calls
                WHERE id = ?
                """,
                (local_call_id,),
            ).fetchone()

        if not target:
            raise ValueError("Call not found for webhook payload.")

        status = call_data.get("call_status") or event
        connection.execute(
            """
            UPDATE calls
            SET
                retell_call_id = COALESCE(?, retell_call_id),
                status = ?,
                transcript = COALESCE(?, transcript),
                duration = COALESCE(?, duration),
                recording_url = COALESCE(?, recording_url),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                call_id,
                status,
                call_data.get("transcript"),
                duration,
                call_data.get("recording_url"),
                target["id"],
            ),
        )
        campaign_id = int(target["campaign_id"])

    refresh_campaign_status(campaign_id)
    updated_call = fetch_one(
        """
        SELECT
            id,
            campaign_id,
            retell_call_id,
            phone,
            name,
            status,
            transcript,
            duration,
            recording_url,
            created_at,
            updated_at
        FROM calls
        WHERE id = ?
        """,
        (int(target["id"]),),
    )
    if not updated_call:
        raise ValueError("Updated call could not be retrieved.")
    return updated_call


def refresh_campaign_status(campaign_id: int) -> None:
    calls = fetch_all(
        """
        SELECT status
        FROM calls
        WHERE campaign_id = ?
        """,
        (campaign_id,),
    )
    if not calls:
        status = "pending"
    elif all(call["status"] in TERMINAL_CALL_STATUSES for call in calls):
        status = "completed"
    else:
        status = "processing"

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE campaigns
            SET status = ?
            WHERE id = ?
            """,
            (status, campaign_id),
        )
