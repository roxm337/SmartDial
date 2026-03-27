from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


PHONE_REGEX = re.compile(r"^\+?[1-9]\d{7,14}$")


class AgentCreate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    script: str = Field(min_length=1)


class AgentRead(BaseModel):
    id: int
    name: str | None
    script: str
    retell_agent_id: str
    retell_llm_id: str | None = None
    created_at: datetime | str

    model_config = ConfigDict(from_attributes=True)


class LeadInput(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        cleaned = value.strip()
        if not PHONE_REGEX.match(cleaned):
            raise ValueError("Phone number must be a valid E.164-like format.")
        return cleaned


class CampaignCreate(BaseModel):
    agent_id: int
    leads: list[LeadInput] = Field(min_length=1)


class CampaignRead(BaseModel):
    id: int
    agent_id: int
    status: str
    created_at: datetime | str
    total_calls: int = 0
    completed_calls: int = 0

    model_config = ConfigDict(from_attributes=True)


class CallRead(BaseModel):
    id: int
    campaign_id: int
    retell_call_id: str | None = None
    phone: str
    name: str | None = None
    status: str
    transcript: str | None = None
    duration: int | None = None
    recording_url: str | None = None
    created_at: datetime | str
    updated_at: datetime | str

    model_config = ConfigDict(from_attributes=True)


class CampaignDetail(CampaignRead):
    calls: list[CallRead]


class MessageResponse(BaseModel):
    message: str
