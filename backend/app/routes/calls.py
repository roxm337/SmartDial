import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.schemas import CallRead, MessageResponse
from app.services.calls import list_calls, update_call_from_webhook


logger = logging.getLogger(__name__)

router = APIRouter(tags=["calls"])


@router.get("/calls", response_model=list[CallRead])
def list_calls_endpoint() -> list[CallRead]:
    calls = list_calls()
    return [CallRead.model_validate(call) for call in calls]


@router.post("/webhook/retell", response_model=MessageResponse)
def retell_webhook_endpoint(payload: dict[str, Any]) -> MessageResponse:
    try:
        event = str(payload.get("event", "unknown"))
        call_payload = payload.get("call", payload)
        if not isinstance(call_payload, dict):
            raise ValueError("Webhook call payload must be an object.")
        update_call_from_webhook(event, call_payload)
    except ValueError as exc:
        logger.warning("Webhook rejected: %s", exc)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return MessageResponse(message="Webhook processed.")
