import os
from typing import Any, Dict, Optional, Tuple

import requests
from urllib.parse import urlparse


def _cred_type(cred: Optional[str]) -> str:
    if not cred:
        return "<missing>"
    k = cred.strip()
    if k.startswith("eyJ"):
        return "jwt(eyJ...)"
    if k.startswith("sb_publishable_"):
        return "sb_publishable"
    if k.startswith("sb_secret_"):
        return "sb_secret"
    if k.startswith("esb_secret_"):
        return "esb_secret"
    return "unknown"


def _safe_host(url: Optional[str]) -> str:
    if not url:
        return "<missing>"
    try:
        parsed = urlparse(url.strip())
        return parsed.netloc or "<unparsed>"
    except Exception:
        return "<unparsed>"


def _get_cfg() -> Tuple[str, str]:
    supabase_url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    supabase_cred = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not supabase_url or not supabase_cred:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return supabase_url, supabase_cred


def _headers(cred: str) -> Dict[str, str]:
    return {
        "apikey": cred,
        "Authorization": f"Bearer {cred}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def sb_debug_hint() -> str:
    try:
        supabase_url, supabase_cred = _get_cfg()
    except Exception:
        supabase_url = (os.getenv("SUPABASE_URL") or "").strip()
        supabase_cred = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    return f"sb_host={_safe_host(supabase_url)} sb_cred_type={_cred_type(supabase_cred)} sb_cred_len={len(supabase_cred)}"


def supabase_rest(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    prefer_return_representation: bool = False,
) -> requests.Response:
    supabase_url, supabase_cred = _get_cfg()

    # Safe diagnostics (do NOT log full secrets).
    print("=== SB CFG ===")
    print(
        f"sb_host={_safe_host(supabase_url)} sb_cred_type={_cred_type(supabase_cred)} sb_cred_len={len(supabase_cred)}"
    )

    url = f"{supabase_url}{path}"
    headers = _headers(supabase_cred)
    if prefer_return_representation:
        headers["Prefer"] = "return=representation"

    # Use requests directly - avoid any Client wrappers that might have proxy issues
    return requests.request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        json=json,
        timeout=30,
    )


def get_supabase() -> None:
    """Backwards-compat stub (old code referenced this)."""
    return None


