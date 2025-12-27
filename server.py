import os
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from whisper_wrapper import get_transcriber
from notion_integration import get_notion_integration

load_dotenv()

app = FastAPI(title="Aha! Catcher API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key for summary generation (still using external API)
API_KEY = os.getenv("SUPER_MIND_API_KEY")
API_BASE_URL = "https://space.ai-builders.com/backend/v1"

if not API_KEY:
    raise RuntimeError("SUPER_MIND_API_KEY not found in .env file")

# Initialize Whisper transcriber
try:
    transcriber = get_transcriber()
except Exception as e:
    print(f"Warning: Could not initialize Whisper transcriber: {e}")
    print("Make sure OPENAI_API_KEY is set in .env file")
    transcriber = None

# Initialize Notion integration
try:
    notion = get_notion_integration()
except Exception as e:
    print(f"Warning: Could not initialize Notion integration: {e}")
    print("Make sure NOTION_INTEGRATION_TOKEN is set in .env file")
    print("Notion save feature will be disabled")
    notion = None


class SummaryRequest(BaseModel):
    text: str


class NotionSaveRequest(BaseModel):
    transcript: str
    summary: Optional[str] = None
    timestamp: Optional[str] = None
    parent_page_id: str


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page"""
    with open("index.html", "r") as f:
        return f.read()


@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Endpoint for OpenAI Whisper transcription.
    Accepts an audio file and returns the transcription.
    Uses OpenAI Whisper API directly via whisper_wrapper.
    """
    if transcriber is None:
        raise HTTPException(
            status_code=500,
            detail="Whisper transcriber not initialized. Please check OPENAI_API_KEY in .env file."
        )
    
    try:
        # Read audio file content
        audio_bytes = await file.read()
        
        # Validate file size (OpenAI limit is 25MB)
        max_size = 25 * 1024 * 1024  # 25MB in bytes
        if len(audio_bytes) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"Audio file too large. Maximum size is 25MB. Your file is {len(audio_bytes) / (1024*1024):.2f}MB"
            )
        
        # Transcribe using Whisper wrapper
        result = transcriber.transcribe_bytes(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.webm",
            response_format="json"  # Returns {"text": "..."} format
        )
        
        return result

    except ValueError as e:
        # Invalid API key or configuration error
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"Connection error: {str(e)}")
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=f"Request timeout: {str(e)}")
    except RuntimeError as e:
        # API errors, rate limits, etc.
        error_msg = str(e)
        status_code = 500
        if "rate limit" in error_msg.lower():
            status_code = 429
        elif "too large" in error_msg.lower():
            status_code = 413
        raise HTTPException(status_code=status_code, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@app.post("/api/summarize")
async def generate_summary(request: SummaryRequest):
    """
    Proxy endpoint for GPT-4 summary generation.
    Accepts transcribed text and returns a research summary.
    """
    try:
        # Load system prompt from file
        system_prompt_path = "system_prompt.md"
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        else:
            # Fallback to default prompt if file not found
            system_prompt = "You are a research assistant. Given a transcription of a spontaneous 'Aha!' moment, extract the key insight and provide a brief, structured summary with: 1) The core insight, 2) Potential applications, and 3) Next steps to explore."

        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            "model": "deepseek",
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
            "max_tokens": 500
        }

        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()

        data = response.json()
        summary = data['choices'][0]['message']['content']

        return {"summary": summary}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Summary API error: {str(e)}")


@app.post("/api/notion/save")
async def save_to_notion(request: NotionSaveRequest):
    """
    Save aha moment to Notion.
    Creates a new page in the specified parent page with transcription and summary.
    """
    if notion is None:
        raise HTTPException(
            status_code=500,
            detail="Notion integration not initialized. Please check NOTION_INTEGRATION_TOKEN in .env file."
        )
    
    try:
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


@app.get("/api/notion/status")
async def notion_status():
    """
    Check if Notion integration is available.
    """
    if notion is None:
        return {
            "available": False,
            "message": "Notion integration not configured. Please set NOTION_INTEGRATION_TOKEN in .env file."
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8002, reload=True)
