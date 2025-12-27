import os
import sys

# Add parent directory to path to import shared helpers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from urllib.parse import urlparse

from clerk_auth import verify_clerk_token
from supabase_client import supabase_rest, sb_debug_hint


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InsightSaveRequest(BaseModel):
    transcript: str = Field(..., min_length=1)
    summary: Optional[str] = None
    title: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class InsightResponse(BaseModel):
    id: str
    user_id: str
    transcript: str
    summary: Optional[str] = None
    title: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: str
    message: str


def _sb_debug_hint() -> str:
    """Backward compat wrapper."""
    return sb_debug_hint()


@app.post("/api/insights/save")
async def save_insight(
    request: InsightSaveRequest,
    user: dict = Depends(verify_clerk_token),
) -> InsightResponse:
    """
    Save an insight to Supabase.

    Security model (Option A):
    - Backend uses SUPABASE_SERVICE_ROLE_KEY (bypasses RLS)
    - Multi-tenancy is enforced in code: user_id is always set from Clerk `sub`
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    try:
        print("\n=== INSIGHTS SAVE ===")
        print(f"Clerk user_id (sub): {user_id}")
        print(f"Transcript length: {len(request.transcript)}")
        print(f"Has summary: {bool((request.summary or '').strip())}")
        print(f"Tags count: {len(request.tags or [])}")
        print("About to call Supabase REST...")

        # Generate a lightweight title if not provided
        title = (request.title or "").strip() or request.transcript[:50].strip()
        if len(request.transcript) > 50 and not (request.title or "").strip():
            title += "..."

        data = {
            "user_id": user_id,
            "transcript": request.transcript,
            "summary": request.summary,
            "title": title,
            "tags": request.tags or [],
        }

        resp = supabase_rest(
            "POST",
            "/rest/v1/insights",
            json=data,
            prefer_return_representation=True,
        )

        if resp.status_code == 401 and "Invalid API key" in (resp.text or ""):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save: Invalid API key ({sb_debug_hint()})",
            )

        if not resp.ok:
            print(f"Supabase REST error status={resp.status_code} body={resp.text[:2000]}")
            raise HTTPException(status_code=500, detail=f"Failed to save: Supabase error {resp.status_code}")

        rows = resp.json() if resp.text else []
        if not rows:
            raise HTTPException(status_code=500, detail="Failed to save insight")

        saved = rows[0]
        return InsightResponse(
            id=saved["id"],
            user_id=saved["user_id"],
            transcript=saved["transcript"],
            summary=saved.get("summary"),
            title=saved.get("title"),
            tags=saved.get("tags") or [],
            created_at=saved["created_at"],
            message="Insight saved successfully!",
        )

    except HTTPException:
        raise
    except Exception as e:
        # Try to extract underlying HTTP error details when available
        print("✗ Exception while saving insight to Supabase")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception repr: {repr(e)}")
        print(f"Exception str: {str(e)}")
        # Common for postgrest/supabase errors
        for attr in ("message", "details", "hint", "code"):
            if hasattr(e, attr):
                try:
                    print(f"Supabase error {attr}: {getattr(e, attr)}")
                except Exception:
                    pass
        # If Supabase rejects the API credential, include a safe hint in the client-visible error.
        if "Invalid API key" in str(e):
            raise HTTPException(status_code=500, detail=f"Failed to save: Invalid API key ({sb_debug_hint()})")

        raise HTTPException(status_code=500, detail=f"Failed to save: {str(e)}")


