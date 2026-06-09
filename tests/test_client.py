from __future__ import annotations

import httpx
import pytest

from tiktok_ads_mcp.client import TikTokAdsClient, TikTokApiError
from tiktok_ads_mcp.config import Settings


@pytest.mark.asyncio
async def test_get_campaigns_encodes_filtering_and_header() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["token"] = request.headers.get("Access-Token")
        seen["query"] = str(request.url.query)
        return httpx.Response(200, json={"code": 0, "message": "OK", "data": {"list": []}})

    transport = httpx.MockTransport(handler)
    settings = Settings(access_token="token", advertiser_id="adv", base_url="https://business-api.tiktok.com")
    client = TikTokAdsClient(settings)
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=settings.base_url,
        transport=transport,
        headers={"Access-Token": settings.access_token, "Content-Type": "application/json"},
    )

    try:
        await client.get_campaigns(filtering={"campaign_ids": ["123"]}, fields=["campaign_id"])
    finally:
        await client.close()

    assert seen["token"] == "token"
    query = seen["query"]
    assert isinstance(query, str)
    assert "advertiser_id=adv" in query
    assert "filtering=" in query
    assert "campaign_ids" in query
    assert "fields=" in query


@pytest.mark.asyncio
async def test_mutation_dry_run_blocks_request() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("dry-run should not send HTTP request")

    settings = Settings(access_token="token", advertiser_id="adv", mutation_mode="live")
    client = TikTokAdsClient(settings)
    await client._client.aclose()
    client._client = httpx.AsyncClient(base_url=settings.base_url, transport=httpx.MockTransport(handler))

    try:
        result = await client.update_campaign(campaign_id="123", budget=50, dry_run=True)
    finally:
        await client.close()

    assert result["dry_run"] is True
    assert result["payload"]["budget"] == 50


@pytest.mark.asyncio
async def test_api_code_error_raises() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 40104, "message": "Access token is null", "data": {}})

    settings = Settings(access_token="token", advertiser_id="adv")
    client = TikTokAdsClient(settings)
    await client._client.aclose()
    client._client = httpx.AsyncClient(base_url=settings.base_url, transport=httpx.MockTransport(handler))

    try:
        with pytest.raises(TikTokApiError):
            await client.get_campaigns()
    finally:
        await client.close()
