from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    access_token: str
    advertiser_id: str | None = None
    base_url: str = "https://business-api.tiktok.com"
    timeout_seconds: float = 30.0
    mutation_mode: str = "dry_run"

    @property
    def live_mutations_enabled(self) -> bool:
        return self.mutation_mode.lower() == "live"


def get_settings() -> Settings:
    token = os.getenv("TIKTOK_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TIKTOK_ACCESS_TOKEN is required.")

    return Settings(
        access_token=token,
        advertiser_id=os.getenv("TIKTOK_ADVERTISER_ID") or None,
        base_url=os.getenv("TIKTOK_API_BASE_URL", "https://business-api.tiktok.com").rstrip("/"),
        timeout_seconds=float(os.getenv("TIKTOK_TIMEOUT_SECONDS", "30")),
        mutation_mode=os.getenv("TIKTOK_MUTATION_MODE", "dry_run"),
    )
