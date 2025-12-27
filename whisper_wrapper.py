"""
Whisper Transcription Wrapper

This module provides a wrapper for OpenAI Whisper API transcription.
It handles audio file transcription with proper error handling and
maintains compatibility with the existing API interface.
"""

import os
import io
from typing import Optional, Dict, Any
from openai import OpenAI
from openai import APIError, APIConnectionError, APITimeoutError


class WhisperTranscriber:
    """
    Wrapper class for OpenAI Whisper API transcription.
    
    Provides a simple interface for transcribing audio files using
    OpenAI's Whisper model via their official API.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "whisper-1"):
        """
        Initialize the Whisper transcriber.
        
        Args:
            api_key: OpenAI API key. If None, will try to get from OPENAI_API_KEY env var.
            model: Whisper model to use (default: "whisper-1")
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
    
    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None,
        response_format: str = "json",
        temperature: float = 0.0,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio from bytes.
        
        Args:
            audio_bytes: Audio file content as bytes
            filename: Original filename (used to determine format)
            language: Optional language code (e.g., "en", "es"). Auto-detected if None.
            response_format: Response format - "json", "text", "srt", "verbose_json", or "vtt"
            temperature: Sampling temperature (0.0 to 1.0). Lower = more deterministic.
            prompt: Optional text prompt to guide the model's style or vocabulary
        
        Returns:
            Dictionary with transcription result. Format depends on response_format.
            For "json" format: {"text": "transcribed text"}
            For "verbose_json": Includes segments, language, duration, etc.
        """
        try:
            # Ensure filename has proper extension for OpenAI
            original_filename = filename
            if not filename or not any(filename.lower().endswith(ext) for ext in ['.webm', '.mp3', '.wav', '.m4a', '.ogg', '.flac', '.mp4', '.mpeg', '.mpga', '.oga']):
                # Default to .webm if no valid extension
                filename = 'recording.webm'

            print(f"[WhisperWrapper] Original filename: {original_filename}, Using: {filename}")

            # Create a file-like object from bytes with proper name attribute
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = filename
            # Ensure we're at the beginning of the buffer
            audio_file.seek(0)

            print(f"[WhisperWrapper] Calling OpenAI API with file.name: {audio_file.name}, size: {len(audio_bytes)} bytes")
            print(f"[WhisperWrapper] File object type: {type(audio_file)}, has name: {hasattr(audio_file, 'name')}")

            # Call OpenAI API - pass the file object directly with .name attribute set
            # Build kwargs excluding None values
            api_kwargs = {
                "model": self.model,
                "file": audio_file,
                "response_format": response_format,
            }

            if language:
                api_kwargs["language"] = language
            if temperature != 0.0:
                api_kwargs["temperature"] = temperature
            if prompt:
                api_kwargs["prompt"] = prompt

            transcript = self.client.audio.transcriptions.create(**api_kwargs)
            print(f"[WhisperWrapper] ✓ API call successful")
            
            # Handle different response formats
            if response_format == "json":
                return {"text": transcript.text}
            elif response_format == "text":
                return {"text": str(transcript)}
            elif response_format == "verbose_json":
                # Convert to dict if it's an object
                if hasattr(transcript, 'model_dump'):
                    return transcript.model_dump()
                elif hasattr(transcript, 'dict'):
                    return transcript.dict()
                else:
                    return {"text": transcript.text}
            else:
                return {"text": transcript.text}
                
        except APIConnectionError as e:
            raise ConnectionError(f"Failed to connect to OpenAI API: {str(e)}")
        except APITimeoutError as e:
            raise TimeoutError(f"OpenAI API request timed out: {str(e)}")
        except APIError as e:
            error_msg = str(e)
            print(f"[WhisperWrapper] ✗ APIError: {error_msg}")
            print(f"[WhisperWrapper] Error type: {type(e)}")
            if hasattr(e, 'response'):
                print(f"[WhisperWrapper] Error response: {e.response}")
            if hasattr(e, 'status_code'):
                print(f"[WhisperWrapper] Status code: {e.status_code}")
                if e.status_code == 401:
                    raise ValueError("Invalid OpenAI API key")
                elif e.status_code == 429:
                    raise RuntimeError("OpenAI API rate limit exceeded. Please try again later.")
                elif e.status_code == 413:
                    raise ValueError("Audio file is too large. Maximum size is 25MB.")
                elif e.status_code == 400:
                    # Include full error details for 400 errors
                    raise RuntimeError(f"OpenAI API validation error (400): {error_msg}")
            raise RuntimeError(f"OpenAI API error: {error_msg}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during transcription: {str(e)}")
    
    def transcribe_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        response_format: str = "json",
        temperature: float = 0.0,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio from a file path.
        
        Args:
            file_path: Path to audio file
            language: Optional language code (e.g., "en", "es"). Auto-detected if None.
            response_format: Response format - "json", "text", "srt", "verbose_json", or "vtt"
            temperature: Sampling temperature (0.0 to 1.0). Lower = more deterministic.
            prompt: Optional text prompt to guide the model's style or vocabulary
        
        Returns:
            Dictionary with transcription result
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        with open(file_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            filename = os.path.basename(file_path)
            
            return self.transcribe_bytes(
                audio_bytes=audio_bytes,
                filename=filename,
                language=language,
                response_format=response_format,
                temperature=temperature,
                prompt=prompt
            )


# Global instance (lazy initialization)
_transcriber_instance: Optional[WhisperTranscriber] = None


def get_transcriber() -> WhisperTranscriber:
    """
    Get or create the global WhisperTranscriber instance.
    
    Returns:
        WhisperTranscriber instance
    """
    global _transcriber_instance
    if _transcriber_instance is None:
        _transcriber_instance = WhisperTranscriber()
    return _transcriber_instance

