from __future__ import annotations

from tiktok_ads_mcp.analysis import extract_rows, propose_campaign_actions


def test_extract_rows_flattens_report_shape() -> None:
    rows = extract_rows(
        {
            "data": {
                "list": [
                    {
                        "dimensions": {"campaign_id": "1"},
                        "metrics": {"spend": "100", "cost_per_conversion": "25"},
                    }
                ]
            }
        }
    )

    assert rows == [{"campaign_id": "1", "spend": "100", "cost_per_conversion": "25"}]


def test_propose_campaign_actions_thresholds() -> None:
    actions = propose_campaign_actions(
        [{"campaign_id": "1", "spend": "100", "cost_per_conversion": "80", "conversions": "1"}],
        min_spend=50,
        max_cpa=60,
        min_conversions=2,
    )

    assert actions[0]["campaign_id"] == "1"
    assert actions[0]["operation_status"] == "DISABLE"
    assert len(actions[0]["reasons"]) == 2
