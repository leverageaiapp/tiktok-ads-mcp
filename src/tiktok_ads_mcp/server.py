from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .analysis import extract_rows, propose_campaign_actions
from .client import TikTokAdsClient
from .config import get_settings

mcp = FastMCP("tiktok-ads")


def _client() -> TikTokAdsClient:
    return TikTokAdsClient(get_settings())


@mcp.tool()
async def tiktok_healthcheck() -> dict[str, Any]:
    """Show local configuration status without exposing secrets."""
    settings = get_settings()
    return {
        "base_url": settings.base_url,
        "default_advertiser_id_set": bool(settings.advertiser_id),
        "live_mutations_enabled": settings.live_mutations_enabled,
        "access_token_set": bool(settings.access_token),
    }


@mcp.tool()
async def get_campaigns(
    advertiser_id: str | None = None,
    filtering: dict[str, Any] | None = None,
    fields: list[str] | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """Get TikTok Ads campaigns. filtering supports TikTok API filters such as campaign_ids/status."""
    async with _client() as client:
        return await client.get_campaigns(advertiser_id, filtering=filtering, fields=fields, page=page, page_size=page_size)


@mcp.tool()
async def get_adgroups(
    advertiser_id: str | None = None,
    filtering: dict[str, Any] | None = None,
    fields: list[str] | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """Get TikTok Ads ad groups. Use filtering for campaign_ids/adgroup_ids/status."""
    async with _client() as client:
        return await client.get_adgroups(advertiser_id, filtering=filtering, fields=fields, page=page, page_size=page_size)


@mcp.tool()
async def get_ads(
    advertiser_id: str | None = None,
    filtering: dict[str, Any] | None = None,
    fields: list[str] | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """Get TikTok Ads ads. Use filtering for campaign_ids/adgroup_ids/ad_ids/status."""
    async with _client() as client:
        return await client.get_ads(advertiser_id, filtering=filtering, fields=fields, page=page, page_size=page_size)


@mcp.tool()
async def get_performance_report(
    advertiser_id: str | None = None,
    report_type: str = "BASIC",
    data_level: str = "AUCTION_CAMPAIGN",
    dimensions: list[str] | None = None,
    metrics: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    filtering: list[dict[str, Any]] | None = None,
    page: int = 1,
    page_size: int = 100,
    order_field: str | None = "spend",
    order_type: str = "DESC",
    enable_total_metrics: bool = False,
) -> dict[str, Any]:
    """Run TikTok's synchronous integrated report endpoint for campaign/adgroup/ad performance."""
    async with _client() as client:
        return await client.get_report(
            report_type=report_type,
            advertiser_id=advertiser_id,
            data_level=data_level,
            dimensions=dimensions,
            metrics=metrics,
            start_date=start_date,
            end_date=end_date,
            filtering=filtering,
            page=page,
            page_size=page_size,
            order_field=order_field,
            order_type=order_type,
            enable_total_metrics=enable_total_metrics,
        )


@mcp.tool()
async def recommend_campaign_actions(
    advertiser_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_spend: float = 50.0,
    max_cpa: float | None = None,
    min_roas: float | None = None,
    min_conversions: float | None = None,
    extra_metrics: list[str] | None = None,
) -> dict[str, Any]:
    """Analyze campaign report rows and propose pause actions based on simple thresholds. Does not mutate."""
    metrics = [
        "spend",
        "impressions",
        "clicks",
        "ctr",
        "cpc",
        "cpm",
        "conversions",
        "cost_per_conversion",
    ]
    if extra_metrics:
        metrics.extend(extra_metrics)
    async with _client() as client:
        report = await client.get_report(
            advertiser_id=advertiser_id,
            data_level="AUCTION_CAMPAIGN",
            dimensions=["campaign_id"],
            metrics=metrics,
            start_date=start_date,
            end_date=end_date,
            page_size=1000,
            order_field="spend",
        )
    rows = extract_rows(report)
    return {
        "rows_analyzed": len(rows),
        "actions": propose_campaign_actions(
            rows,
            min_spend=min_spend,
            max_cpa=max_cpa,
            min_roas=min_roas,
            min_conversions=min_conversions,
        ),
    }


@mcp.tool()
async def update_campaign(
    campaign_id: str,
    advertiser_id: str | None = None,
    campaign_name: str | None = None,
    budget: float | None = None,
    budget_mode: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Update campaign fields such as name or budget. Defaults to dry-run."""
    async with _client() as client:
        return await client.update_campaign(
            advertiser_id=advertiser_id,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            budget=budget,
            budget_mode=budget_mode,
            dry_run=dry_run,
        )


@mcp.tool()
async def update_campaign_status(
    campaign_ids: list[str],
    operation_status: str,
    advertiser_id: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Enable, disable, or delete campaigns. operation_status is typically ENABLE, DISABLE, or DELETE."""
    async with _client() as client:
        return await client.update_campaign_status(
            advertiser_id=advertiser_id,
            campaign_ids=campaign_ids,
            operation_status=operation_status,
            dry_run=dry_run,
        )


@mcp.tool()
async def update_adgroup(
    adgroup_id: str,
    advertiser_id: str | None = None,
    adgroup_name: str | None = None,
    budget: float | None = None,
    bid_price: float | None = None,
    conversion_bid_price: float | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Update ad group fields such as budget or bid. Defaults to dry-run."""
    async with _client() as client:
        return await client.update_adgroup(
            advertiser_id=advertiser_id,
            adgroup_id=adgroup_id,
            adgroup_name=adgroup_name,
            budget=budget,
            bid_price=bid_price,
            conversion_bid_price=conversion_bid_price,
            dry_run=dry_run,
        )


@mcp.tool()
async def update_adgroup_status(
    adgroup_ids: list[str],
    operation_status: str,
    advertiser_id: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Enable, disable, or delete ad groups. operation_status is typically ENABLE, DISABLE, or DELETE."""
    async with _client() as client:
        return await client.update_adgroup_status(
            advertiser_id=advertiser_id,
            adgroup_ids=adgroup_ids,
            operation_status=operation_status,
            dry_run=dry_run,
        )


@mcp.tool()
async def update_ad_status(
    ad_ids: list[str],
    operation_status: str,
    advertiser_id: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Enable, disable, or delete ads. operation_status is typically ENABLE, DISABLE, or DELETE."""
    async with _client() as client:
        return await client.update_ad_status(
            advertiser_id=advertiser_id,
            ad_ids=ad_ids,
            operation_status=operation_status,
            dry_run=dry_run,
        )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
