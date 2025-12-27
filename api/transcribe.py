import os
import sys
import traceback

# Add parent directory to path to import whisper_wrapper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from whisper_wrapper import get_transcriber
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

# Initialize transcriber at module level (cold start optimization)
transcriber = None

print("=== TRANSCRIBE API INITIALIZATION ===")
print(f"OPENAI_API_KEY exists: {bool(os.getenv('OPENAI_API_KEY'))}")
print(f"OPENAI_API_KEY length: {len(os.getenv('OPENAI_API_KEY', ''))}")
print(f"OPENAI_API_KEY prefix: {os.getenv('OPENAI_API_KEY', '')[:10]}...")

try:
    transcriber = get_transcriber()
    print("✓ Whisper transcriber initialized successfully")
except Exception as e:
    print(f"✗ ERROR initializing Whisper transcriber: {e}")
    print(f"Traceback: {traceback.format_exc()}")


@app.post("/api/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    user: dict = Depends(verify_clerk_token)
):
    """
    Endpoint for OpenAI Whisper transcription.
    Accepts an audio file and returns the transcription.
    """
    print("\n=== TRANSCRIBE REQUEST ===")
    print(f"User ID: {user.get('sub', 'unknown')}")
    print(f"File received: {file.filename}")
    print(f"Content type: {file.content_type}")

    if transcriber is None:
        print("✗ ERROR: Transcriber is None")
        raise HTTPException(
            status_code=500,
            detail="Whisper transcriber not initialized. Please check OPENAI_API_KEY environment variable."
        )

    try:
        # Read audio file content
        print("Reading audio file...")
        audio_bytes = await file.read()
        print(f"Audio file size: {len(audio_bytes)} bytes ({len(audio_bytes) / 1024:.2f} KB, {len(audio_bytes) / (1024*1024):.2f} MB)")

        # Debug: Show first bytes to verify file format
        import binascii
        first_32 = audio_bytes[:32]
        print(f"First 32 bytes (hex): {binascii.hexlify(first_32).decode()}")

        # Check if it's actually a valid webm file
        webm_magic = b'\x1a\x45\xdf\xa3'
        if audio_bytes[:4] == webm_magic:
            print("✓ File has valid WebM/EBML header")
        else:
            print(f"✗ File does NOT have valid WebM header!")
            print(f"  Expected: {binascii.hexlify(webm_magic).decode()}")
            print(f"  Got: {binascii.hexlify(audio_bytes[:4]).decode()}")

        # Validate file size (OpenAI limit is 25MB)
        max_size = 25 * 1024 * 1024  # 25MB in bytes
        if len(audio_bytes) > max_size:
            print(f"✗ File too large: {len(audio_bytes) / (1024*1024):.2f}MB")
            raise HTTPException(
                status_code=413,
                detail=f"Audio file too large. Maximum size is 25MB. Your file is {len(audio_bytes) / (1024*1024):.2f}MB"
            )

        # Transcribe using Whisper wrapper
        actual_filename = file.filename or "audio.webm"
        print(f"Calling Whisper API with filename: {actual_filename}")
        result = transcriber.transcribe_bytes(
            audio_bytes=audio_bytes,
            filename=actual_filename,
            response_format="json"
        )
        print(f"✓ Transcription successful: {result.get('text', '')[:100]}...")

        return result

    except ValueError as e:
        print(f"✗ ValueError: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except ConnectionError as e:
        print(f"✗ ConnectionError: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=503, detail=f"Connection error: {str(e)}")
    except TimeoutError as e:
        print(f"✗ TimeoutError: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=504, detail=f"Request timeout: {str(e)}")
    except RuntimeError as e:
        error_msg = str(e)
        print(f"✗ RuntimeError: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        status_code = 500
        if "rate limit" in error_msg.lower():
            status_code = 429
        elif "too large" in error_msg.lower():
            status_code = 413
        raise HTTPException(status_code=status_code, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")
