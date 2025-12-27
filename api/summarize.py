import os
import sys
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

# Configuration
API_KEY = os.getenv("SUPER_MIND_API_KEY")
API_BASE_URL = "https://space.ai-builders.com/backend/v1"
MAX_TOKENS = int(os.getenv("SUPER_MIND_MAX_TOKENS", "2000"))
MODEL = os.getenv("SUPER_MIND_MODEL", "deepseek")

# Load system prompt
SYSTEM_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "system_prompt.md"
)

# Default system prompt if file not found
DEFAULT_SYSTEM_PROMPT = (
    "You are a research assistant. Given a transcription of a spontaneous 'Aha!' moment, "
    "extract the key insight and provide a brief, structured summary with: "
    "1) The core insight, 2) Potential applications, and 3) Next steps to explore."
)


def load_system_prompt():
    """Load system prompt from file or return default."""
    try:
        if os.path.exists(SYSTEM_PROMPT_PATH):
            with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        print(f"Warning: Could not load system prompt: {e}")
    return DEFAULT_SYSTEM_PROMPT


class SummaryRequest(BaseModel):
    text: str


@app.post("/api/summarize")
async def generate_summary(
    request: SummaryRequest,
    user: dict = Depends(verify_clerk_token)
):
    """
    Endpoint for GPT-4 summary generation.
    Accepts transcribed text and returns a research summary.
    """
    print("\n=== SUMMARIZE REQUEST ===")
    print(f"User ID: {user.get('sub', 'unknown')}")
    print(f"API_KEY exists: {bool(API_KEY)}")
    print(f"API_KEY length: {len(API_KEY) if API_KEY else 0}")
    if API_KEY:
        print(f"API_KEY prefix: {API_KEY[:6]}...")  # safe-ish, do not log full key
    print(f"API_BASE_URL: {API_BASE_URL}")
    print(f"Text to summarize (first 100 chars): {request.text[:100]}...")
    print(f"MODEL: {MODEL}")
    print(f"MAX_TOKENS: {MAX_TOKENS}")

    if not API_KEY:
        print("✗ ERROR: API_KEY not set")
        raise HTTPException(
            status_code=500,
            detail="SUPER_MIND_API_KEY not configured. Please set environment variable."
        )

    try:
        # Load system prompt
        system_prompt = load_system_prompt()
        print(f"System prompt loaded, length: {len(system_prompt)}")

        # Prepare API request
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": request.text
                }
            ],
            "temperature": 0.7,
            # NOTE: very large max_tokens is a common cause of upstream 500s.
            "max_tokens": MAX_TOKENS
        }

        print(f"Calling SUPER_MIND API at {API_BASE_URL}/chat/completions")

        # Call external API
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )

        print(f"Response status code: {response.status_code}")
        # Helpful for provider-side debugging (if they include request IDs)
        req_id = response.headers.get("x-request-id") or response.headers.get("x-amzn-requestid")
        if req_id:
            print(f"Upstream request id: {req_id}")

        if not response.ok:
            print("✗ API error response")
            print(f"Upstream status: {response.status_code}")
            print(f"Upstream headers (subset): content-type={response.headers.get('content-type')}")
            print(f"Upstream body (first 2000 chars): {response.text[:2000]}")

        response.raise_for_status()

        data = response.json()
        print("✓ Summary API call successful")

        # Check if response was truncated
        finish_reason = data['choices'][0].get('finish_reason', 'unknown')
        print(f"Finish reason: {finish_reason}")
        if finish_reason == 'length':
            print("⚠️ WARNING: Response was truncated due to max_tokens limit!")

        summary = data['choices'][0]['message']['content']
        print(f"Summary length: {len(summary)} characters")

        return {"summary": summary}

    except requests.exceptions.RequestException as e:
        print(f"✗ RequestException: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response headers (subset): content-type={e.response.headers.get('content-type')}")
            print(f"Response body (first 2000 chars): {e.response.text[:2000]}")
        raise HTTPException(status_code=500, detail=f"Summary API error: {str(e)}")
    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
