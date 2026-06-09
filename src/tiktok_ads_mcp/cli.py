from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from .analysis import extract_rows, propose_campaign_actions
from .client import TikTokAdsClient, TikTokApiError
from .config import get_settings


def json_arg(value: str | None) -> Any:
    if value in (None, ""):
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"Invalid JSON: {exc}") from exc


def csv_arg(value: str | None) -> list[str] | None:
    if value in (None, ""):
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


async def run(args: argparse.Namespace) -> dict[str, Any]:
    async with TikTokAdsClient(get_settings()) as client:
        if args.command == "campaigns":
            return await client.get_campaigns(
                args.advertiser_id,
                filtering=json_arg(args.filtering),
                fields=csv_arg(args.fields),
                page=args.page,
                page_size=args.page_size,
            )
        if args.command == "adgroups":
            return await client.get_adgroups(
                args.advertiser_id,
                filtering=json_arg(args.filtering),
                fields=csv_arg(args.fields),
                page=args.page,
                page_size=args.page_size,
            )
        if args.command == "ads":
            return await client.get_ads(
                args.advertiser_id,
                filtering=json_arg(args.filtering),
                fields=csv_arg(args.fields),
                page=args.page,
                page_size=args.page_size,
            )
        if args.command == "report":
            return await client.get_report(
                advertiser_id=args.advertiser_id,
                report_type=args.report_type,
                data_level=args.data_level,
                dimensions=csv_arg(args.dimensions),
                metrics=csv_arg(args.metrics),
                start_date=args.start_date,
                end_date=args.end_date,
                filtering=json_arg(args.filtering),
                page=args.page,
                page_size=args.page_size,
                order_field=args.order_field,
                order_type=args.order_type,
                enable_total_metrics=args.enable_total_metrics,
            )
        if args.command == "recommend":
            report = await client.get_report(
                advertiser_id=args.advertiser_id,
                data_level="AUCTION_CAMPAIGN",
                dimensions=["campaign_id"],
                metrics=csv_arg(args.metrics)
                or ["spend", "impressions", "clicks", "conversions", "cost_per_conversion"],
                start_date=args.start_date,
                end_date=args.end_date,
                page_size=1000,
                order_field="spend",
            )
            rows = extract_rows(report)
            return {
                "rows_analyzed": len(rows),
                "actions": propose_campaign_actions(
                    rows,
                    min_spend=args.min_spend,
                    max_cpa=args.max_cpa,
                    min_roas=args.min_roas,
                    min_conversions=args.min_conversions,
                ),
            }
        if args.command == "campaign-update":
            return await client.update_campaign(
                advertiser_id=args.advertiser_id,
                campaign_id=args.campaign_id,
                campaign_name=args.name,
                budget=args.budget,
                budget_mode=args.budget_mode,
                dry_run=not args.live,
            )
        if args.command == "campaign-status":
            return await client.update_campaign_status(
                advertiser_id=args.advertiser_id,
                campaign_ids=args.campaign_ids,
                operation_status=args.operation_status,
                dry_run=not args.live,
            )
        if args.command == "adgroup-update":
            return await client.update_adgroup(
                advertiser_id=args.advertiser_id,
                adgroup_id=args.adgroup_id,
                adgroup_name=args.name,
                budget=args.budget,
                bid_price=args.bid_price,
                conversion_bid_price=args.conversion_bid_price,
                dry_run=not args.live,
            )
        if args.command == "adgroup-status":
            return await client.update_adgroup_status(
                advertiser_id=args.advertiser_id,
                adgroup_ids=args.adgroup_ids,
                operation_status=args.operation_status,
                dry_run=not args.live,
            )
        if args.command == "ad-status":
            return await client.update_ad_status(
                advertiser_id=args.advertiser_id,
                ad_ids=args.ad_ids,
                operation_status=args.operation_status,
                dry_run=not args.live,
            )
    raise ValueError(f"Unknown command: {args.command}")


def add_common_read_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--advertiser-id")
    parser.add_argument("--filtering", help='JSON filter, for example {"campaign_ids":["123"]}')
    parser.add_argument("--fields", help="Comma-separated fields")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=50)


def add_common_write_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--advertiser-id")
    parser.add_argument("--live", action="store_true", help="Execute mutation. Also requires TIKTOK_MUTATION_MODE=live.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TikTok Ads MCP companion CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    add_common_read_args(sub.add_parser("campaigns", help="List campaigns"))
    add_common_read_args(sub.add_parser("adgroups", help="List ad groups"))
    add_common_read_args(sub.add_parser("ads", help="List ads"))

    report = sub.add_parser("report", help="Run an integrated performance report")
    report.add_argument("--advertiser-id")
    report.add_argument("--report-type", default="BASIC")
    report.add_argument("--data-level", default="AUCTION_CAMPAIGN")
    report.add_argument("--dimensions", default="campaign_id")
    report.add_argument("--metrics", default="spend,impressions,clicks,ctr,cpc,cpm,conversions,cost_per_conversion")
    report.add_argument("--start-date")
    report.add_argument("--end-date")
    report.add_argument("--filtering")
    report.add_argument("--page", type=int, default=1)
    report.add_argument("--page-size", type=int, default=100)
    report.add_argument("--order-field", default="spend")
    report.add_argument("--order-type", default="DESC")
    report.add_argument("--enable-total-metrics", action="store_true")

    rec = sub.add_parser("recommend", help="Suggest campaign pause actions from thresholds")
    rec.add_argument("--advertiser-id")
    rec.add_argument("--start-date")
    rec.add_argument("--end-date")
    rec.add_argument("--metrics")
    rec.add_argument("--min-spend", type=float, default=50.0)
    rec.add_argument("--max-cpa", type=float)
    rec.add_argument("--min-roas", type=float)
    rec.add_argument("--min-conversions", type=float)

    cu = sub.add_parser("campaign-update", help="Update campaign name/budget")
    add_common_write_args(cu)
    cu.add_argument("campaign_id")
    cu.add_argument("--name")
    cu.add_argument("--budget", type=float)
    cu.add_argument("--budget-mode")

    cs = sub.add_parser("campaign-status", help="Update campaign status")
    add_common_write_args(cs)
    cs.add_argument("operation_status", choices=["ENABLE", "DISABLE", "DELETE"])
    cs.add_argument("campaign_ids", nargs="+")

    au = sub.add_parser("adgroup-update", help="Update ad group budget/bid/name")
    add_common_write_args(au)
    au.add_argument("adgroup_id")
    au.add_argument("--name")
    au.add_argument("--budget", type=float)
    au.add_argument("--bid-price", type=float)
    au.add_argument("--conversion-bid-price", type=float)

    ags = sub.add_parser("adgroup-status", help="Update ad group status")
    add_common_write_args(ags)
    ags.add_argument("operation_status", choices=["ENABLE", "DISABLE", "DELETE"])
    ags.add_argument("adgroup_ids", nargs="+")

    ads = sub.add_parser("ad-status", help="Update ad status")
    add_common_write_args(ads)
    ads.add_argument("operation_status", choices=["ENABLE", "DISABLE", "DELETE"])
    ads.add_argument("ad_ids", nargs="+")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = asyncio.run(run(args))
    except (TikTokApiError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
