from fastapi import APIRouter, HTTPException, status

from app.schemas import CampaignCreate, CampaignDetail, CampaignRead
from app.services.calls import create_campaign, list_campaigns


router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignDetail, status_code=status.HTTP_201_CREATED)
async def create_campaign_endpoint(payload: CampaignCreate) -> CampaignDetail:
    try:
        campaign = await create_campaign(
            agent_id=payload.agent_id,
            leads=[lead.model_dump() for lead in payload.leads],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return CampaignDetail.model_validate(campaign)


@router.get("", response_model=list[CampaignRead])
def list_campaigns_endpoint() -> list[CampaignRead]:
    campaigns = list_campaigns()
    return [CampaignRead.model_validate(campaign) for campaign in campaigns]

