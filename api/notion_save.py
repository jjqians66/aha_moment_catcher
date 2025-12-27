import os
import sys

# Add parent directory to path to import notion_integration
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from notion_integration import get_notion_integration
from clerk_auth import verify_clerk_token

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Notion integration at module level (cold start optimization)
notion = None

try:
    notion = get_notion_integration()
except Exception as e:
    print(f"Warning: Could not initialize Notion integration: {e}")


class NotionSaveRequest(BaseModel):
    transcript: str
    summary: Optional[str] = None
    timestamp: Optional[str] = None
    parent_page_id: str


@app.post("/api/notion/save")
async def save_to_notion(
    request: NotionSaveRequest,
    user: dict = Depends(verify_clerk_token)
):
    """
    Save aha moment to Notion.
    Creates a new page in the specified parent page with transcription and summary.
    """
    print(f"\n=== NOTION SAVE from user: {user.get('sub', 'unknown')} ===")

    if notion is None:
        raise HTTPException(
            status_code=500,
            detail="Notion integration not initialized. Please check NOTION_INTEGRATION_TOKEN environment variable."
        )

    try:
        # Create Notion page
        result = notion.create_aha_page(
            parent_page_id=request.parent_page_id,
            transcript=request.transcript,
            summary=request.summary,
            timestamp=request.timestamp
        )

        return {
            "success": True,
            "message": "Aha moment saved to Notion successfully",
            "page_url": result.get("page_url"),
            "page_id": result.get("page_id")
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        error_msg = str(e)
        status_code = 500
        if "rate limit" in error_msg.lower():
            status_code = 429
        raise HTTPException(status_code=status_code, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save to Notion: {str(e)}")
