"""Agent proxy routes for Multi-Agent chat integration."""
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from core.config import get_settings

router = APIRouter(tags=["agent"])


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    messages: List[ChatMessage]
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    success: bool
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response from agent health check."""
    success: bool
    status: str
    endpoint: Optional[str] = None
    host: Optional[str] = None
    auth_configured: bool


async def get_oauth_token(settings) -> str:
    """Get OAuth token using Service Principal credentials."""
    if not settings.databricks_client_id or not settings.databricks_client_secret:
        raise HTTPException(
            status_code=500,
            detail="Missing Service Principal credentials"
        )

    token_url = f"https://{settings.databricks_server_hostname}/oidc/v1/token"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "scope": "all-apis",
                "client_id": settings.databricks_client_id,
                "client_secret": settings.databricks_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"OAuth token request failed: {response.text}"
            )

        return response.json()["access_token"]


def get_agent_endpoint() -> str:
    """Get the agent endpoint name from environment.

    The endpoint name follows the pattern: agents_{catalog}-{schema}-{agent_name}
    This must be set via DATABRICKS_AGENT_ENDPOINT environment variable.
    """
    endpoint = os.getenv("DATABRICKS_AGENT_ENDPOINT")
    if not endpoint:
        raise HTTPException(
            status_code=500,
            detail="DATABRICKS_AGENT_ENDPOINT environment variable not set"
        )
    return endpoint


@router.get("/agent/health", response_model=HealthResponse)
async def health_check():
    """Check agent endpoint health and configuration."""
    settings = get_settings()

    has_credentials = bool(
        settings.databricks_client_id and
        settings.databricks_client_secret
    )

    return HealthResponse(
        success=True,
        status="healthy" if has_credentials else "unconfigured",
        endpoint=get_agent_endpoint(),
        host=settings.databricks_server_hostname,
        auth_configured=has_credentials,
    )


@router.post("/agent/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Proxy chat messages to the Multi-Agent serving endpoint.

    This endpoint handles OAuth authentication and forwards messages
    to the Databricks Model Serving endpoint.
    """
    settings = get_settings()

    try:
        # Check for authentication
        if not settings.is_service_principal:
            # For local development with PAT token
            token = settings.databricks_token
            if not token:
                return ChatResponse(
                    success=False,
                    error="No authentication configured. Set DATABRICKS_TOKEN for local dev or Service Principal for production."
                )
        else:
            # Production: Get OAuth token
            token = await get_oauth_token(settings)

        # Build agent payload
        agent_payload = {
            "input": [
                {"role": msg.role, "content": msg.content, "type": "text"}
                for msg in request.messages
            ],
            "custom_inputs": request.context or {},
        }

        # Call agent endpoint
        endpoint_name = get_agent_endpoint()
        agent_url = f"https://{settings.databricks_server_hostname}/serving-endpoints/{endpoint_name}/invocations"

        print(f"Calling agent endpoint: {agent_url}")
        print(f"Payload: {agent_payload}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                agent_url,
                json=agent_payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code != 200:
                error_detail = response.text
                print(f"Agent error: {response.status_code} - {error_detail}")
                return ChatResponse(
                    success=False,
                    error=f"Agent error: {response.status_code} - {error_detail}"
                )

            agent_response = response.json()
            print(f"Agent response: {agent_response}")

            return ChatResponse(success=True, response=agent_response)

    except httpx.TimeoutException:
        return ChatResponse(
            success=False,
            error="Request timed out. Please try a simpler question."
        )
    except Exception as e:
        print(f"Agent proxy error: {e}")
        return ChatResponse(success=False, error=str(e))
