# Whisper Transcription Wrapper - Implementation Plan

## Current State Analysis

### Current Implementation
- **Endpoint**: `/api/transcribe`
- **External API**: `https://space.ai-builders.com/backend/v1/audio/transcriptions`
- **Model**: Likely OpenAI Whisper (based on endpoint comment and standard API patterns)
- **Input**: Multipart form data with audio file
- **Output**: JSON with `text` field containing transcription

### What We Know
1. The current implementation is a proxy to an external API
2. The comment says "OpenAI Whisper transcription"
3. The API accepts audio files and returns text transcriptions
4. No explicit model specification in the current code

## Implementation Options

### Option 1: OpenAI Whisper API (Recommended for Production)
**Pros:**
- Official OpenAI API
- High accuracy
- No local model loading
- Handles various audio formats
- Supports multiple languages
- No GPU required on server

**Cons:**
- Requires OpenAI API key
- Cost per minute of audio
- External dependency

**Implementation:**
- Use `openai` Python library
- Call `openai.Audio.transcriptions.create()`
- Support multiple audio formats (mp3, mp4, mpeg, mpga, m4a, wav, webm)

### Option 2: Local Whisper Model (Recommended for Self-Hosted)
**Pros:**
- No API costs
- Complete control
- No external dependencies
- Privacy (audio stays local)
- Works offline

**Cons:**
- Requires GPU for reasonable speed
- Model loading time
- Higher memory usage
- Need to handle model downloads

**Implementation:**
- Use `openai-whisper` Python package (official)
- Or use `transformers` library with Whisper models
- Load model on startup or lazy load
- Support multiple model sizes (tiny, base, small, medium, large)

### Option 3: Hybrid Approach
**Pros:**
- Fallback if API fails
- Can switch between local and API
- Best of both worlds

**Cons:**
- More complex code
- Need to manage both options

## Recommended Approach: Option 1 (OpenAI API) with Option 2 (Local) as Fallback

### Architecture

```
┌─────────────────┐
│  FastAPI Server │
│                 │
│  /api/transcribe│
└────────┬────────┘
         │
         ├───► OpenAI Whisper API (Primary)
         │     - Fast, accurate
         │     - Requires API key
         │
         └───► Local Whisper Model (Fallback)
               - Self-hosted
               - No API costs
               - Requires GPU/CPU
```

## Implementation Plan

### Phase 1: OpenAI Whisper API Wrapper
1. **Install Dependencies**
   ```bash
   pip install openai
   ```

2. **Create Wrapper Class**
   - `WhisperTranscriber` class
   - Methods:
     - `transcribe_file(file_path)` - transcribe from file path
     - `transcribe_bytes(audio_bytes, filename)` - transcribe from bytes
   - Configuration:
     - Model selection (whisper-1)
     - Language (optional, auto-detect)
     - Response format (text, json, verbose_json, srt, vtt)

3. **Integrate with FastAPI**
   - Replace current proxy endpoint
   - Handle file uploads
   - Return same response format
   - Error handling

### Phase 2: Local Whisper Model Wrapper (Optional)
1. **Install Dependencies**
   ```bash
   pip install openai-whisper
   # OR
   pip install transformers torch torchaudio
   ```

2. **Create Local Transcriber**
   - Model loading (lazy or on startup)
   - Audio preprocessing
   - Transcription with timestamps
   - Memory management

3. **Configuration**
   - Model size selection (tiny/base/small/medium/large)
   - Device selection (cuda/cpu)
   - Batch processing for long audio

### Phase 3: Unified Interface
1. **Transcriber Interface**
   - Abstract base class or protocol
   - Both implementations follow same interface
   - Easy switching between implementations

2. **Configuration Management**
   - Environment variables for API keys
   - Model selection
   - Fallback logic

## File Structure

```
aha_catcher/
├── server.py                 # Main FastAPI app
├── whisper_wrapper.py         # New: Whisper wrapper implementation
├── config.py                  # New: Configuration management
├── .env                       # API keys and config
└── requirements.txt           # Updated dependencies
```

## API Response Format

### Current Format
```json
{
  "text": "Transcribed text here..."
}
```

### Enhanced Format (Optional)
```json
{
  "text": "Transcribed text here...",
  "language": "en",
  "duration": 30.5,
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "First segment..."
    }
  ]
}
```

## Error Handling

1. **API Errors**
   - Rate limiting
   - Invalid API key
   - File format issues
   - Network errors

2. **Local Model Errors**
   - Model loading failures
   - Out of memory
   - Unsupported audio format
   - GPU unavailable

3. **Fallback Logic**
   - Try OpenAI API first
   - Fall back to local model if API fails
   - Return appropriate error messages

## Configuration Options

### Environment Variables
```bash
# OpenAI API (Option 1)
OPENAI_API_KEY=sk-...

# Local Model (Option 2)
WHISPER_MODEL_SIZE=base  # tiny, base, small, medium, large
WHISPER_DEVICE=cuda      # cuda or cpu
USE_LOCAL_WHISPER=false  # true to use local, false for API

# Fallback
ENABLE_FALLBACK=true     # Enable fallback to local if API fails
```

## Testing Plan

1. **Unit Tests**
   - Test transcription with sample audio
   - Test error handling
   - Test different audio formats

2. **Integration Tests**
   - Test with FastAPI endpoint
   - Test file upload handling
   - Test response format

3. **Performance Tests**
   - Measure transcription time
   - Test with different audio lengths
   - Memory usage monitoring

## Implementation Steps

1. ✅ Create plan document (this file)
2. ⏳ Install OpenAI Python library
3. ⏳ Create `whisper_wrapper.py` with OpenAI API implementation
4. ⏳ Update `server.py` to use new wrapper
5. ⏳ Add configuration management
6. ⏳ Test with sample audio files
7. ⏳ Add error handling and logging
8. ⏳ (Optional) Add local Whisper model support
9. ⏳ (Optional) Add fallback logic
10. ⏳ Update documentation

## Dependencies

### Required
- `openai` - OpenAI Python library for API access
- `python-multipart` - Already installed for FastAPI file uploads

### Optional (for local model)
- `openai-whisper` - Official Whisper package
- `torch` - PyTorch for local model inference
- `torchaudio` - Audio processing
- `ffmpeg` - Audio format conversion (system dependency)

## Cost Considerations

### OpenAI Whisper API
- Pricing: $0.006 per minute (as of 2024)
- Example: 30 seconds = $0.003
- Very affordable for MVP

### Local Model
- No per-use cost
- Requires GPU for reasonable performance
- Higher initial setup complexity

## Next Steps

1. Start with OpenAI API wrapper (simplest, most reliable)
2. Test thoroughly
3. Add local model support if needed
4. Implement fallback logic
5. Optimize for production use



