from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import Settings


class TikTokApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, response: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


@dataclass(frozen=True)
class MutationPreview:
    endpoint: str
    payload: dict[str, Any]
    dry_run: bool
    live_allowed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "live_allowed": self.live_allowed,
            "endpoint": self.endpoint,
            "payload": self.payload,
            "message": "Preview only. Set dry_run=false and TIKTOK_MUTATION_MODE=live to execute.",
        }


class TikTokAdsClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
            headers={
                "Access-Token": settings.access_token,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "TikTokAdsClient":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._client.request(
            method.upper(),
            endpoint,
            params=self._encode_params(params or {}),
            json=json_body,
        )
        data = self._parse_json(response)

        if response.status_code >= 400:
            raise TikTokApiError(
                f"TikTok API HTTP {response.status_code}: {data.get('message') or response.text}",
                status_code=response.status_code,
                response=data,
            )

        api_code = data.get("code")
        if api_code not in (None, 0):
            raise TikTokApiError(
                f"TikTok API error {api_code}: {data.get('message', 'unknown error')}",
                status_code=response.status_code,
                response=data,
            )

        return data

    def _parse_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            parsed = response.json()
        except ValueError as exc:
            raise TikTokApiError(
                f"TikTok API returned non-JSON response: {response.text[:300]}",
                status_code=response.status_code,
            ) from exc
        if not isinstance(parsed, dict):
            raise TikTokApiError("TikTok API returned a non-object JSON payload.", status_code=response.status_code)
        return parsed

    def _encode_params(self, params: dict[str, Any]) -> dict[str, Any]:
        encoded: dict[str, Any] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                encoded[key] = json.dumps(value, separators=(",", ":"))
            elif isinstance(value, bool):
                encoded[key] = "true" if value else "false"
            else:
                encoded[key] = value
        return encoded

    def advertiser_id(self, advertiser_id: str | None) -> str:
        resolved = advertiser_id or self.settings.advertiser_id
        if not resolved:
            raise ValueError("advertiser_id is required. Pass it explicitly or set TIKTOK_ADVERTISER_ID.")
        return resolved

    async def get_campaigns(
        self,
        advertiser_id: str | None = None,
        *,
        filtering: dict[str, Any] | None = None,
        fields: list[str] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            "/open_api/v1.3/campaign/get/",
            params={
                "advertiser_id": self.advertiser_id(advertiser_id),
                "filtering": filtering,
                "fields": fields,
                "page": page,
                "page_size": page_size,
            },
        )

    async def get_adgroups(
        self,
        advertiser_id: str | None = None,
        *,
        filtering: dict[str, Any] | None = None,
        fields: list[str] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            "/open_api/v1.3/adgroup/get/",
            params={
                "advertiser_id": self.advertiser_id(advertiser_id),
                "filtering": filtering,
                "fields": fields,
                "page": page,
                "page_size": page_size,
            },
        )

    async def get_ads(
        self,
        advertiser_id: str | None = None,
        *,
        filtering: dict[str, Any] | None = None,
        fields: list[str] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            "/open_api/v1.3/ad/get/",
            params={
                "advertiser_id": self.advertiser_id(advertiser_id),
                "filtering": filtering,
                "fields": fields,
                "page": page,
                "page_size": page_size,
            },
        )

    async def get_report(
        self,
        *,
        report_type: str = "BASIC",
        advertiser_id: str | None = None,
        advertiser_ids: list[str] | None = None,
        data_level: str = "AUCTION_CAMPAIGN",
        dimensions: list[str] | None = None,
        metrics: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        filtering: list[dict[str, Any]] | None = None,
        page: int = 1,
        page_size: int = 100,
        order_field: str | None = None,
        order_type: str = "DESC",
        enable_total_metrics: bool = False,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            "/open_api/v1.3/report/integrated/get/",
            params={
                "report_type": report_type,
                "advertiser_id": advertiser_id or (None if advertiser_ids else self.settings.advertiser_id),
                "advertiser_ids": advertiser_ids,
                "data_level": data_level,
                "dimensions": dimensions or ["campaign_id"],
                "metrics": metrics or ["spend", "impressions", "clicks", "ctr", "cpc", "cpm", "conversions", "cost_per_conversion"],
                "start_date": start_date,
                "end_date": end_date,
                "filtering": filtering,
                "page": page,
                "page_size": page_size,
                "order_field": order_field,
                "order_type": order_type,
                "enable_total_metrics": enable_total_metrics,
            },
        )

    async def mutate(self, endpoint: str, payload: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        preview = MutationPreview(endpoint, payload, dry_run, self.settings.live_mutations_enabled)
        if dry_run or not self.settings.live_mutations_enabled:
            return preview.as_dict()
        return await self.request("POST", endpoint, json_body=payload)

    async def update_campaign(
        self,
        *,
        campaign_id: str,
        advertiser_id: str | None = None,
        dry_run: bool = True,
        **updates: Any,
    ) -> dict[str, Any]:
        payload = {"advertiser_id": self.advertiser_id(advertiser_id), "campaign_id": campaign_id, **self._clean(updates)}
        return await self.mutate("/open_api/v1.3/campaign/update/", payload, dry_run=dry_run)

    async def update_campaign_status(
        self,
        *,
        campaign_ids: list[str],
        operation_status: str,
        advertiser_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "advertiser_id": self.advertiser_id(advertiser_id),
            "campaign_ids": campaign_ids,
            "operation_status": operation_status,
        }
        return await self.mutate("/open_api/v1.3/campaign/status/update/", payload, dry_run=dry_run)

    async def update_adgroup(
        self,
        *,
        adgroup_id: str,
        advertiser_id: str | None = None,
        dry_run: bool = True,
        **updates: Any,
    ) -> dict[str, Any]:
        payload = {"advertiser_id": self.advertiser_id(advertiser_id), "adgroup_id": adgroup_id, **self._clean(updates)}
        return await self.mutate("/open_api/v1.3/adgroup/update/", payload, dry_run=dry_run)

    async def update_adgroup_status(
        self,
        *,
        adgroup_ids: list[str],
        operation_status: str,
        advertiser_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "advertiser_id": self.advertiser_id(advertiser_id),
            "adgroup_ids": adgroup_ids,
            "operation_status": operation_status,
        }
        return await self.mutate("/open_api/v1.3/adgroup/status/update/", payload, dry_run=dry_run)

    async def update_ad_status(
        self,
        *,
        ad_ids: list[str],
        operation_status: str,
        advertiser_id: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "advertiser_id": self.advertiser_id(advertiser_id),
            "ad_ids": ad_ids,
            "operation_status": operation_status,
        }
        return await self.mutate("/open_api/v1.3/ad/status/update/", payload, dry_run=dry_run)

    def _clean(self, values: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in values.items() if value is not None}
