import os
import sys

# Add parent directory to path to import shared helpers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from clerk_auth import verify_clerk_token
from supabase_client import supabase_rest


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/insights")
async def list_insights(
    user: dict = Depends(verify_clerk_token),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = None,
):
    """List user's insights with pagination and optional search."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    try:
        print("\n=== INSIGHTS LIST ===")
        print(f"Clerk user_id (sub): {user_id}")
        print(f"limit={limit} offset={offset} search={search!r}")

        # PostgREST filters via query params
        params = {
            "user_id": f"eq.{user_id}",
            "select": "*",
            "order": "created_at.desc",
            "limit": str(limit),
            "offset": str(offset),
        }

        # Optional text search: PostgREST supports `or` for ilike
        if search:
            s = search.replace("%", "\\%").replace("_", "\\_")
            params["or"] = f"(transcript.ilike.%{s}%,summary.ilike.%{s}%,title.ilike.%{s}%)"

        resp = supabase_rest("GET", "/rest/v1/insights", params=params)
        if not resp.ok:
            print(f"Supabase REST error status={resp.status_code} body={resp.text[:2000]}")
            raise HTTPException(status_code=500, detail=f"Failed to list insights: Supabase error {resp.status_code}")

        insights = resp.json() if resp.text else []

        # Count query
        count_params = {"user_id": f"eq.{user_id}", "select": "id"}
        count_resp = supabase_rest("GET", "/rest/v1/insights", params=count_params)
        total_count = len(count_resp.json() if count_resp.ok and count_resp.text else [])

        return {
            "insights": insights,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }

    except Exception as e:
        print("✗ Exception while listing insights from Supabase")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception str: {str(e)}")
        resp = getattr(e, "response", None)
        if resp is not None:
            try:
                print(f"Supabase HTTP status: {getattr(resp, 'status_code', None)}")
                print(f"Supabase HTTP body: {getattr(resp, 'text', None)}")
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to list insights: {str(e)}")


@app.get("/api/insights/{insight_id}")
async def get_insight(
    insight_id: str,
    user: dict = Depends(verify_clerk_token),
):
    """Get a single insight by ID (must belong to the current user)."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    try:
        params = {"id": f"eq.{insight_id}", "user_id": f"eq.{user_id}", "select": "*"}
        resp = supabase_rest("GET", "/rest/v1/insights", params=params)
        if not resp.ok:
            raise HTTPException(status_code=500, detail=f"Failed to get insight: Supabase error {resp.status_code}")

        rows = resp.json() if resp.text else []
        if not rows:
            raise HTTPException(status_code=404, detail="Insight not found")
        return rows[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get insight: {str(e)}")


@app.delete("/api/insights/{insight_id}")
async def delete_insight(
    insight_id: str,
    user: dict = Depends(verify_clerk_token),
):
    """Delete an insight by ID (must belong to the current user)."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    try:
        params = {"id": f"eq.{insight_id}", "user_id": f"eq.{user_id}"}
        resp = supabase_rest("DELETE", "/rest/v1/insights", params=params)
        if not resp.ok:
            print(f"Supabase REST error status={resp.status_code} body={resp.text[:2000]}")
            raise HTTPException(status_code=500, detail=f"Failed to delete insight: Supabase error {resp.status_code}")
        return {"success": True, "message": "Insight deleted"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete insight: {str(e)}"
        )


