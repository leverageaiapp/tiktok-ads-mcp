# TikTok Ads MCP

MCP server and CLI for TikTok Ads reporting plus controlled campaign/ad group/ad adjustments. It is designed for agent workflows where a teammate wants to inspect performance and make small operational changes without using Ads Manager.

Ground truth is TikTok Business API v1.3. The implementation uses the official endpoint family under `https://business-api.tiktok.com/open_api/v1.3/`, including campaign get/update/status update, ad group get/update/status update, ad get/status update, and integrated reporting.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Set at least:

```bash
export TIKTOK_ACCESS_TOKEN="..."
export TIKTOK_ADVERTISER_ID="..."
```

For live mutations, you must also set:

```bash
export TIKTOK_MUTATION_MODE=live
```

Even with that env var, all MCP write tools and CLI write commands default to dry-run.

## MCP Usage

Add this to your MCP client config:

```json
{
  "mcpServers": {
    "tiktok-ads": {
      "command": "tiktok-ads-mcp",
      "cwd": "/Users/louis/Desktop/coding/tiktok-ads-mcp",
      "env": {
        "TIKTOK_ACCESS_TOKEN": "your_access_token",
        "TIKTOK_ADVERTISER_ID": "your_advertiser_id",
        "TIKTOK_MUTATION_MODE": "dry_run"
      }
    }
  }
}
```

Useful tools:

- `get_performance_report`: run TikTok integrated reporting.
- `get_campaigns`, `get_adgroups`, `get_ads`: inspect account structure.
- `recommend_campaign_actions`: produce threshold-based pause recommendations, no mutation.
- `update_campaign`, `update_campaign_status`: update budget/name/status.
- `update_adgroup`, `update_adgroup_status`, `update_ad_status`: update ad group/ad settings or status.

Example agent instruction:

> Pull campaign performance for 2026-06-01 to 2026-06-07. Identify campaigns with spend over 100 and CPA over 40. Show me the candidates first. Do not mutate unless I approve.

## CLI Usage

```bash
tiktok-ads campaigns --page-size 20
tiktok-ads report --start-date 2026-06-01 --end-date 2026-06-07 \
  --dimensions campaign_id \
  --metrics spend,impressions,clicks,conversions,cost_per_conversion
tiktok-ads recommend --start-date 2026-06-01 --end-date 2026-06-07 --min-spend 100 --max-cpa 40
```

Dry-run mutation:

```bash
tiktok-ads campaign-status DISABLE 1234567890
tiktok-ads adgroup-update 9876543210 --budget 50
```

Live mutation:

```bash
export TIKTOK_MUTATION_MODE=live
tiktok-ads campaign-status DISABLE 1234567890 --live
```

## API Notes

TikTok requires the access token in the `Access-Token` header, not `Authorization: Bearer`. Query parameters like `filtering`, `fields`, `dimensions`, and `metrics` are encoded as compact JSON strings when they are lists or objects.

References checked while building:

- Official TikTok Business API portal: https://business-api.tiktok.com/portal/docs
- Official SDK docs list campaign endpoints including `/campaign/get/`, `/campaign/update/`, and `/campaign/status/update/`: https://github.com/tiktok/tiktok-business-api-sdk/blob/main/js_sdk/docs/CampaignCreationApi.md
- Official SDK docs list `/report/integrated/get/`: https://github.com/tiktok/tiktok-business-api-sdk/blob/main/js_sdk/docs/ReportingApi.md
- Community MCP read-only reference: https://github.com/ysntony/tiktok-ads-mcp
- Community AdsMCP reference, useful but less complete in public README and no release package: https://github.com/AdsMCP/tiktok-ads-mcp-server

## Test

```bash
pytest
```
