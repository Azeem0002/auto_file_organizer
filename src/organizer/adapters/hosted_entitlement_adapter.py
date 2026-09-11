
from __future__ import annotations

import os

import httpx

from loguru import logger


def fetch_hosted_entitlement()-> dict[str, object] | None:

    api_url = os.getenv("ORGANIZER_BILLING_API_URL","").rstrip("/")
    access_token= os.getenv("ORGANIZER_ACCESS_TOKEN", "").strip("/")
    if not api_url