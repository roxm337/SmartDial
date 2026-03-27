from fastapi import APIRouter, HTTPException, status

from app.db import execute, fetch_one
from app.schemas import AgentCreate, AgentRead
from app.services.calls import list_agents
from app.services.retell import create_agent


router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent_endpoint(payload: AgentCreate) -> AgentRead:
    try:
        retell_agent = await create_agent(script=payload.script, name=payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    agent_id = execute(
        """
        INSERT INTO agents (name, script, retell_agent_id, retell_llm_id)
        VALUES (?, ?, ?, ?)
        """,
        (
            payload.name,
            payload.script,
            retell_agent["retell_agent_id"],
            retell_agent["retell_llm_id"],
        ),
    )

    agent = fetch_one(
        """
        SELECT id, name, script, retell_agent_id, retell_llm_id, created_at
        FROM agents
        WHERE id = ?
        """,
        (agent_id,),
    )
    if not agent:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Agent created but could not be retrieved.")
    return AgentRead.model_validate(agent)


@router.get("", response_model=list[AgentRead])
def list_agents_endpoint() -> list[AgentRead]:
    return [AgentRead.model_validate(agent) for agent in list_agents()]
