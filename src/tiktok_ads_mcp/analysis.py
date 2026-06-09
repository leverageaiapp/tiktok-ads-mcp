from __future__ import annotations

from typing import Any


def coerce_float(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_rows(report_response: dict[str, Any]) -> list[dict[str, Any]]:
    raw = report_response.get("data", {}).get("list", [])
    rows: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        dimensions = row.get("dimensions") or {}
        metrics = row.get("metrics") or {}
        rows.append({**dimensions, **metrics})
    return rows


def propose_campaign_actions(
    rows: list[dict[str, Any]],
    *,
    min_spend: float = 50.0,
    max_cpa: float | None = None,
    min_roas: float | None = None,
    min_conversions: float | None = None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for row in rows:
        campaign_id = str(row.get("campaign_id") or "")
        if not campaign_id:
            continue

        spend = coerce_float(row.get("spend")) or 0.0
        cpa = coerce_float(row.get("cost_per_conversion") or row.get("cost_per_result"))
        conversions = coerce_float(row.get("conversions") or row.get("conversion") or row.get("result"))
        roas = coerce_float(row.get("total_purchase_roas") or row.get("onsite_shopping_roas") or row.get("roas"))

        reasons: list[str] = []
        if spend >= min_spend and max_cpa is not None and cpa is not None and cpa > max_cpa:
            reasons.append(f"CPA {cpa:.2f} is above threshold {max_cpa:.2f}")
        if spend >= min_spend and min_roas is not None and roas is not None and roas < min_roas:
            reasons.append(f"ROAS {roas:.2f} is below threshold {min_roas:.2f}")
        if spend >= min_spend and min_conversions is not None and (conversions or 0.0) < min_conversions:
            reasons.append(f"Conversions {conversions or 0:.0f} below threshold {min_conversions:.0f}")

        if reasons:
            actions.append(
                {
                    "campaign_id": campaign_id,
                    "suggested_action": "DISABLE",
                    "operation_status": "DISABLE",
                    "spend": spend,
                    "cpa": cpa,
                    "roas": roas,
                    "conversions": conversions,
                    "reasons": reasons,
                }
            )
    return actions
