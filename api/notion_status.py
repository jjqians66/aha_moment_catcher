import os
import sys

# Add parent directory to path to import notion_integration
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/api/notion/status")
async def notion_status(user: dict = Depends(verify_clerk_token)):
    """
    Check if Notion integration is available.
    """
    print(f"\n=== NOTION STATUS from user: {user.get('sub', 'unknown')} ===")

    if notion is None:
        return {
            "available": False,
            "message": "Notion integration not configured. Please set NOTION_INTEGRATION_TOKEN environment variable."
        }

    try:
        # Test connection
        is_connected = notion.test_connection()
        return {
            "available": True,
            "connected": is_connected,
            "message": "Notion integration is ready" if is_connected else "Notion integration configured but connection test failed"
        }
    except Exception as e:
        return {
            "available": True,
            "connected": False,
            "message": f"Notion integration error: {str(e)}"
        }
