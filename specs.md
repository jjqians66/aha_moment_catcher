# Aha! Catcher MVP - Technical Specifications

## Overview

Aha! Catcher is a web-based MVP application that allows users to capture spontaneous moments of insight by recording audio, transcribing it, and generating AI-powered research summaries. The application provides a simple interface for recording audio, viewing transcriptions, requesting research summaries on demand, and saving everything to Notion for cloud-based organization and access.

## Features

### Core Functionality
1. **Audio Recording**
   - Manual start/stop recording (no auto-start)
   - Toggle button that turns green when recording
   - Circular buffer for last 30 seconds of audio
   - Real-time buffer status display

2. **Audio Transcription**
   - Automatic transcription after recording stops
   - Uses OpenAI Whisper API directly (no proxy)
   - Displays transcription immediately
   - Supports multiple audio formats (mp3, wav, webm, m4a, etc.)
   - File size validation (25MB limit)

3. **Research Summary Generation**
   - On-demand GPT-powered research summaries
   - "Send to GPT" button appears after transcription
   - Markdown-formatted output with proper rendering
   - System prompt loaded from `system_prompt.md`

4. **Notion Integration**
   - Save aha moments to Notion pages
   - "Save to Notion" button appears after transcription
   - Creates formatted pages with timestamp, transcription, and research summary
   - Uses Internal Integration Token (simpler MVP approach)
   - Page ID configuration via UI
   - Clickable link to view saved page

5. **User Interface**
   - Modern, gradient-based design
   - Status indicators (ready, recording, processing, error)
   - Responsive layout
   - Clear visual feedback for all actions

## Architecture

### Frontend
- **Technology**: Vanilla HTML, CSS, JavaScript
- **Markdown Rendering**: Marked.js (CDN)
- **Audio API**: MediaRecorder API
- **Communication**: Fetch API for REST calls

### Backend
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn
- **Transcription**: OpenAI Whisper API (direct integration via `whisper_wrapper.py`)
- **Summary Generation**: DeepSeek model via external API proxy
- **Note Keeping**: Notion API integration (via `notion_integration.py`)
- **File Handling**: Multipart form data for audio uploads

## File Structure

```
aha_catcher/
├── index.html              # Frontend application
├── server.py               # FastAPI backend server
├── whisper_wrapper.py      # OpenAI Whisper API wrapper
├── notion_integration.py   # Notion API wrapper
├── system_prompt.md        # System prompt for GPT research summaries
├── .env                    # Environment variables (API keys)
├── specs.md                # This file
├── whisper_wrapper_plan.md # Whisper migration planning document
├── WHISPER_MIGRATION.md    # Whisper migration summary
├── note_keeping.md         # Notion integration planning document
└── NOTION_SETUP.md         # Notion setup guide
```

## Implementation Steps

### Phase 1: Initial Setup
1. Created FastAPI server (`server.py`)
   - Set up CORS middleware
   - Configured environment variable loading
   - Created root endpoint to serve HTML

2. Created HTML frontend (`index.html`)
   - Basic UI structure
   - Status display
   - Capture button

### Phase 2: Audio Recording
1. **Microphone Access**
   - Requested microphone permissions on page load
   - Configured audio settings (echo cancellation, noise suppression, 16kHz sample rate)

2. **MediaRecorder Setup**
   - Created MediaRecorder with WebM/Opus codec
   - Implemented circular buffer for 30-second audio retention
   - Set up chunk-based recording (1-second intervals)

3. **Recording Toggle**
   - Changed from auto-start to manual toggle
   - Button changes text and color when recording
   - Green gradient when active
   - Clears buffer and previous results on new recording

### Phase 3: Transcription Integration (Initial)
1. **Backend Transcription Endpoint**
   - Created `/api/transcribe` endpoint
   - Accepts multipart form data (audio file)
   - Initially proxied to external API (`https://space.ai-builders.com/backend/v1`)
   - Returns transcription text

2. **Frontend Transcription Flow**
   - Sends audio blob to backend after recording stops
   - Displays transcription in results section
   - Shows "Send to GPT" button after successful transcription

### Phase 7: Whisper Migration (Latest)
1. **Created Whisper Wrapper (`whisper_wrapper.py`)**
   - Implemented `WhisperTranscriber` class
   - Direct integration with OpenAI Whisper API
   - Comprehensive error handling (rate limits, API errors, connection issues)
   - Support for multiple audio formats
   - Maintains backward compatibility with existing API interface

2. **Updated Transcription Endpoint**
   - Replaced external API proxy with direct Whisper integration
   - Added file size validation (25MB limit)
   - Enhanced error handling with specific HTTP status codes
   - Improved error messages for better debugging

3. **Benefits of Migration**
   - Direct integration (no proxy layer)
   - Faster and more reliable
   - Better error handling
   - Cost transparency ($0.006/minute)
   - Official OpenAI API support

### Phase 4: Research Summary Generation
1. **Backend Summary Endpoint**
   - Created `/api/summarize` endpoint
   - Loads system prompt from `system_prompt.md` file
   - Falls back to default prompt if file not found
   - Uses DeepSeek model via API proxy
   - Returns formatted summary

2. **System Prompt Management**
   - Created `system_prompt.md` with comprehensive research assistant prompt
   - Prompt includes instructions for:
     - Capturing essence of ideas
     - Market research
     - Validation signals
     - Risk assessment
     - Output formatting

3. **Frontend Summary Flow**
   - "Send to GPT" button triggers summary generation
   - Button only appears after transcription
   - Shows loading state during generation
   - Displays formatted markdown output

### Phase 5: Markdown Rendering
1. **Markdown Library Integration**
   - Added Marked.js via CDN
   - Converts markdown to HTML on client side

2. **Styling for Markdown Elements**
   - Custom CSS for headers (h2, h3)
   - Styled lists (ul, ol)
   - Bold text formatting
   - Code block styling
   - Proper spacing and typography

3. **Fallback Converter**
   - Implemented basic markdown-to-HTML converter
   - Handles headers, bold, lists, paragraphs
   - Used if Marked.js fails to load

### Phase 6: User Experience Improvements
1. **Status Management**
   - Clear status messages for each state
   - Color-coded status indicators
   - Error handling with user-friendly messages

2. **Button States**
   - Disabled states during processing
   - Visual feedback (hover, active states)
   - Conditional visibility

3. **Results Display**
   - Separate sections for transcription and summary
   - Results appear after transcription
   - Summary section updates when GPT response arrives

### Phase 8: Notion Integration
1. **Created Notion Wrapper (`notion_integration.py`)**
   - Implemented `NotionIntegration` class
   - Uses Notion API with Internal Integration Token
   - Creates formatted pages with structured content
   - Handles page creation with blocks (headings, paragraphs, dividers)
   - Comprehensive error handling

2. **Backend Notion Endpoints**
   - Created `POST /api/notion/save` endpoint
   - Accepts transcript, summary, timestamp, and parent page ID
   - Creates formatted Notion page with sections
   - Returns page URL for user access
   - Created `GET /api/notion/status` endpoint for checking integration status

3. **Frontend Notion Integration**
   - Added "Save to Notion" button (appears after transcription)
   - Page ID input field for configuration
   - Saves both transcription and research summary
   - Status feedback and error handling
   - Clickable link to view saved page

4. **Notion Page Structure**
   - Title with timestamp
   - Captured date/time section
   - Transcription section with full text
   - Research Summary section (or "Not generated" if not created)
   - Formatted with Notion blocks (headings, paragraphs, dividers)

5. **Benefits**
   - Cloud-based storage for aha moments
   - Easy access and organization in Notion
   - Formatted, structured pages
   - No additional cost (uses Notion free tier)

## API Endpoints

### `GET /`
- **Purpose**: Serve the main HTML page
- **Response**: HTML content

### `POST /api/transcribe`
- **Purpose**: Transcribe audio file
- **Request**: Multipart form data with audio file
- **Response**: JSON with transcription text `{"text": "..."}`
- **API**: OpenAI Whisper API (direct integration)
- **Model**: `whisper-1`
- **File Size Limit**: 25MB
- **Supported Formats**: mp3, mp4, mpeg, mpga, m4a, wav, webm
- **Error Handling**: 
  - 401: Invalid API key
  - 413: File too large
  - 429: Rate limit exceeded
  - 503: Connection error
  - 504: Request timeout

### `POST /api/summarize`
- **Purpose**: Generate research summary from transcription
- **Request**: JSON with `text` field
- **Response**: JSON with `summary` field (markdown formatted)
- **External API**: DeepSeek model via proxy
- **System Prompt**: Loaded from `system_prompt.md`

### `POST /api/notion/save`
- **Purpose**: Save aha moment to Notion
- **Request**: JSON with `transcript`, `summary` (optional), `timestamp` (optional), `parent_page_id`
- **Response**: JSON with `success`, `page_url`, `page_id`
- **API**: Notion API (via `notion-client` library)
- **Authentication**: Internal Integration Token
- **Error Handling**:
  - 400: Invalid request (missing page ID, empty transcript)
  - 429: Rate limit exceeded
  - 500: API error or configuration error

### `GET /api/notion/status`
- **Purpose**: Check if Notion integration is available
- **Response**: JSON with `available`, `connected`, `message`
- **Use**: Frontend checks this to show/hide save button

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: API key for OpenAI Whisper transcription (required)
- `SUPER_MIND_API_KEY`: API key for external AI services (for summary generation)
- `NOTION_INTEGRATION_TOKEN`: Notion Internal Integration Token (required for Notion save feature)
- Stored in `.env` file (not committed to version control)

### API Configuration

**Transcription (OpenAI Whisper)**
- API: OpenAI Whisper API (direct)
- Model: `whisper-1`
- Endpoint: `openai.Audio.transcriptions.create()`
- Cost: $0.006 per minute

**Summary Generation (External API)**
- Base URL: `https://space.ai-builders.com/backend/v1`
- Chat endpoint: `/chat/completions`
- Model: `deepseek`

**Note Keeping (Notion API)**
- API: Notion API (via `notion-client` library)
- Authentication: Internal Integration Token
- Rate Limit: 3 requests per second
- Cost: Free tier available

## Dependencies

### Backend (Python)
```
fastapi
uvicorn
requests
python-dotenv
python-multipart
pydantic
openai              # OpenAI Whisper API integration
notion-client       # Notion API integration
```

### Frontend (CDN)
- Marked.js: `https://cdn.jsdelivr.net/npm/marked/marked.min.js`

## Setup Instructions

1. **Install Python Dependencies**
   ```bash
   pip3 install fastapi uvicorn requests python-dotenv python-multipart pydantic openai notion-client
   ```

2. **Configure Environment**
   - Create `.env` file
   - Add required API keys:
     ```bash
     OPENAI_API_KEY=sk-your-openai-api-key-here
     SUPER_MIND_API_KEY=your-super-mind-api-key-here
     NOTION_INTEGRATION_TOKEN=secret_your-notion-token-here
     ```
   - `OPENAI_API_KEY` is required for transcription
   - `SUPER_MIND_API_KEY` is required for summary generation
   - `NOTION_INTEGRATION_TOKEN` is required for Notion save feature

3. **Set Up Notion Integration**
   - Create Notion integration at https://www.notion.so/my-integrations
   - Copy Internal Integration Token
   - Create a page in Notion and share it with your integration
   - Get Page ID from the page URL
   - See `NOTION_SETUP.md` for detailed instructions

3. **Start Server**
   ```bash
   python3 server.py
   ```

4. **Access Application**
   - Open browser to `http://localhost:8002`
   - Grant microphone permissions when prompted

## Key Design Decisions

1. **Manual Recording Start**: Prevents accidental recordings and gives users control
2. **Separate Transcription and Summary**: Allows users to review transcription before requesting summary
3. **System Prompt from File**: Makes it easy to update prompt without code changes
4. **Markdown Rendering**: Provides rich formatting for research summaries
5. **Circular Buffer**: Efficiently manages 30-second audio window
6. **Status Indicators**: Clear visual feedback for all application states
7. **Direct Whisper Integration**: Using OpenAI API directly instead of proxy for better reliability and transparency
8. **Modular Wrapper Design**: `whisper_wrapper.py` provides clean abstraction for transcription logic
9. **Notion Integration**: Cloud-based storage using Internal Integration Token for simplicity (MVP approach)
10. **User-Configurable Page ID**: Allows users to choose where to save notes without backend changes

## Migration History

### Whisper API Migration
- **Date**: December 2024
- **Change**: Migrated from external API proxy to direct OpenAI Whisper API
- **Reason**: Better reliability, transparency, and error handling
- **Impact**: 
  - Removed dependency on `https://space.ai-builders.com/backend/v1/audio/transcriptions`
  - Added `whisper_wrapper.py` module
  - Requires `OPENAI_API_KEY` environment variable
  - Improved error handling and file size validation
- **Backward Compatibility**: Maintained (same API response format)

### Notion Integration (Latest)
- **Date**: December 2024
- **Change**: Added Notion integration for saving aha moments
- **Reason**: Cloud-based storage and organization of captured insights
- **Implementation**: Internal Integration Token approach (simpler MVP)
- **Impact**:
  - Added `notion_integration.py` module
  - Added `POST /api/notion/save` and `GET /api/notion/status` endpoints
  - Added "Save to Notion" button in frontend
  - Requires `NOTION_INTEGRATION_TOKEN` environment variable
  - Users need to configure Page ID in UI
- **Future**: Can be upgraded to OAuth 2.0 for multi-user support

## Future Enhancements

- Audio playback functionality
- Save transcriptions locally
- Export summaries
- Multiple recording sessions
- Edit transcriptions before sending to GPT
- Custom system prompts per user
- Audio quality indicators
- Transcription confidence scores
- Local Whisper model support as fallback
- Transcription caching
- Support for verbose_json format (with timestamps)
- Language detection and reporting
- **Notion Enhancements**:
  - OAuth 2.0 support for multi-user scenarios
  - Save Page ID in localStorage for convenience
  - Database integration (store all moments in Notion database)
  - Custom page templates
  - Tags and categories
  - Batch saving
  - Multiple cloud providers (Google Docs, Obsidian, etc.)

## Technical Notes

- Audio format: WebM with Opus codec (falls back to WebM if Opus not supported)
- Buffer duration: 30 seconds (configurable via `BUFFER_DURATION` constant)
- Chunk size: 1 second intervals for efficient buffer management
- Server port: 8002 (configurable in `server.py`)
- Auto-reload: Enabled for development (can be disabled for production)
- Transcription API: OpenAI Whisper API (direct integration)
- Transcription cost: $0.006 per minute of audio
- Maximum file size: 25MB (OpenAI Whisper API limit)
- Supported audio formats: mp3, mp4, mpeg, mpga, m4a, wav, webm

