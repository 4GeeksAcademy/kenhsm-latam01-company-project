from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import httpx


class BrasalandAPIError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class BrasalandAPIClient:
    """Small HTTP client for the existing Brasaland incidents and operations APIs."""

    def __init__(self, *, base_url: str | None = None, token: str | None = None, client: httpx.AsyncClient | None = None):
        self.base_url = (base_url or os.getenv("BRASALAND_API_BASE_URL", "http://127.0.0.1:8010")).rstrip("/")
        self.token = token if token is not None else os.getenv("BRASALAND_API_TOKEN", "")
        self._client = client

    async def _request(self, method: str, path: str, *, json: dict[str, Any] | None = None) -> Any:
        if not self.token:
            raise BrasalandAPIError(503, "API_CREDENTIALS_MISSING", "BRASALAND_API_TOKEN is not configured.")
        headers = {"Authorization": f"Bearer {self.token}"}
        if self._client is not None:
            response = await self._client.request(method, f"{self.base_url}{path}", headers=headers, json=json)
        else:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.request(method, f"{self.base_url}{path}", headers=headers, json=json)
        if response.is_error:
            code, message = _error_details(response)
            raise BrasalandAPIError(response.status_code, code, message)
        return response.json()

    async def create_incident(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/api/incidents", json=payload)

    async def get_incident(self, incident_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/incidents/{quote(incident_id, safe='')}")

    async def update_incident_status(self, incident_id: str, status: str) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/incidents/{quote(incident_id, safe='')}/status",
            json={"status": status},
        )

    async def list_inventory(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/operations/inventory")


def _error_details(response: httpx.Response) -> tuple[str, str]:
    try:
        detail = response.json().get("detail", {})
    except (ValueError, AttributeError):
        detail = {}
    if isinstance(detail, dict):
        message = detail.get("message") or str(detail)
        if detail.get("fields"):
            message = f"{message} Fields: {detail['fields']}"
    else:
        message = str(detail) if detail else response.text[:300]
    code = {
        400: "VALIDATION_ERROR",
        401: "API_UNAUTHENTICATED",
        403: "API_FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
    }.get(response.status_code, "API_ERROR")
    return code, message
