# Note Keeping Integration - Implementation Plan

## Overview

Add functionality to save aha moments (transcription and research summary) to cloud-based note-taking services, starting with Notion as the primary integration.

## User Journey

1. User records audio and generates transcription
2. User optionally generates research summary
3. User clicks "Save" button
4. System prompts for Notion authentication (if not already authenticated)
5. User authorizes access to their Notion workspace
6. System creates a new Notion page with:
   - Timestamp (date/time of capture)
   - Transcript (full transcription text)
   - Research Summary (if generated, otherwise marked as "Not generated")
7. User receives confirmation that note was saved

## Implementation Options

### Option 1: Notion API (Recommended)

**Pros:**
- Official API with good documentation
- Free tier available
- Rich formatting support
- Database/page creation
- OAuth 2.0 authentication
- Well-maintained Python SDK

**Cons:**
- Requires OAuth setup
- Rate limits (3 requests per second)
- Requires Notion account

**Implementation:**
- Use `notion-client` Python library
- OAuth 2.0 flow for authentication
- Create pages in user's Notion workspace
- Store access tokens securely

### Option 2: Google Docs API

**Pros:**
- Widely used
- Free
- Good API support
- OAuth 2.0

**Cons:**
- More complex API
- Requires Google Cloud project setup
- Less structured than Notion

### Option 3: Obsidian (via Obsidian URI)

**Pros:**
- Popular markdown-based note app
- Simple file-based storage
- No API needed (can use file system)

**Cons:**
- Requires Obsidian installed locally
- Not truly cloud-based
- Limited to local machine

### Option 4: Multiple Providers (Future)

**Pros:**
- User choice
- More flexibility

**Cons:**
- More complex implementation
- Multiple OAuth flows to manage

## Recommended Approach: Notion API

### Architecture

```
┌─────────────┐
│   Frontend  │
│  "Save" btn │
└──────┬──────┘
       │
       ├───► OAuth Flow (Notion)
       │     - Redirect to Notion
       │     - User authorizes
       │     - Return with code
       │
       └───► Backend API
             - Exchange code for token
             - Store token securely
             - Create Notion page
             - Return success/error
```

## Implementation Plan

### Phase 1: Backend Setup

#### 1.1 Notion API Integration
- **Dependencies**: `notion-client`, `requests`
- **Setup**:
  1. Create Notion integration at https://www.notion.so/my-integrations
  2. Get integration token (Internal Integration)
  3. For OAuth: Create OAuth app, get client_id and client_secret
  4. Set up redirect URI

#### 1.2 Backend Endpoints

**`POST /api/notion/auth/initiate`**
- Purpose: Start OAuth flow
- Request: `{}`
- Response: `{"auth_url": "https://api.notion.com/v1/oauth/authorize?..."}`
- Returns authorization URL for frontend redirect

**`GET /api/notion/auth/callback`**
- Purpose: Handle OAuth callback
- Request: Query params with `code` and `state`
- Response: `{"success": true, "access_token": "..."}`
- Exchanges authorization code for access token
- Stores token securely (encrypted in database or session)

**`POST /api/notion/save`**
- Purpose: Save aha moment to Notion
- Request:
  ```json
  {
    "transcript": "transcription text",
    "summary": "research summary (optional)",
    "timestamp": "2024-12-10T12:00:00Z"
  }
  ```
- Response: `{"success": true, "page_url": "https://notion.so/..."}`
- Creates Notion page with structured content

**`GET /api/notion/status`**
- Purpose: Check if user is authenticated
- Response: `{"authenticated": true/false}`

#### 1.3 Token Storage

**Options:**
1. **Session-based** (Simple, but lost on server restart)
   - Store in server memory/session
   - Good for MVP

2. **Database** (Recommended for production)
   - Store encrypted tokens in database
   - Associate with user session/ID
   - Allows persistence across sessions

3. **Environment Variable** (For single-user/internal use)
   - Store integration token directly
   - Simplest but least flexible

**Recommendation**: Start with session-based, migrate to database later.

### Phase 2: Frontend Integration

#### 2.1 UI Changes

**Add "Save to Notion" Button**
- Location: Below "Send to GPT" button
- Visibility: Show after transcription is generated
- States:
  - Default: "💾 Save to Notion"
  - Loading: "Saving..."
  - Success: "✅ Saved!"
  - Error: "❌ Save Failed"

**Authentication Flow**
- If not authenticated:
  1. Click "Save to Notion"
  2. Opens Notion OAuth page in new window/tab
  3. User authorizes
  4. Redirects back to app
  5. Token stored
  6. Retry save operation
- If authenticated:
  - Direct save without prompt

#### 2.2 JavaScript Functions

```javascript
// Check authentication status
async function checkNotionAuth() {
  const response = await fetch('/api/notion/status');
  return await response.json();
}

// Initiate OAuth flow
async function initiateNotionAuth() {
  const response = await fetch('/api/notion/auth/initiate');
  const data = await response.json();
  window.open(data.auth_url, 'notion-auth', 'width=600,height=700');
}

// Save to Notion
async function saveToNotion(transcript, summary, timestamp) {
  const response = await fetch('/api/notion/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      transcript,
      summary: summary || null,
      timestamp: timestamp || new Date().toISOString()
    })
  });
  return await response.json();
}
```

### Phase 3: Notion Page Structure

#### 3.1 Page Content Format

```
📝 Aha Moment - [Timestamp]

📅 Captured: [Date and Time]

📝 Transcription
[Full transcript text]

🔍 Research Summary
[Summary text or "Not generated"]
```

#### 3.2 Notion Blocks Structure

```python
blocks = [
    {
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": [{"type": "text", "text": {"content": "Aha Moment"}}]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": f"Captured: {timestamp}"}}]
        }
    },
    {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "Transcription"}}]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": transcript}}]
        }
    },
    {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "Research Summary"}}]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": summary or "Not generated"}}]
        }
    }
]
```

### Phase 4: Error Handling

#### 4.1 Error Scenarios

1. **Not Authenticated**
   - Prompt user to authenticate
   - Show clear instructions

2. **Token Expired**
   - Detect expired token
   - Re-initiate OAuth flow
   - Clear old token

3. **Rate Limit Exceeded**
   - Show friendly message
   - Suggest retry after delay

4. **Notion API Error**
   - Log error details
   - Show user-friendly message
   - Allow retry

5. **Network Error**
   - Show connection error
   - Allow retry

#### 4.2 Error Messages

```javascript
const ERROR_MESSAGES = {
  'not_authenticated': 'Please connect your Notion account first.',
  'token_expired': 'Your Notion connection expired. Please reconnect.',
  'rate_limit': 'Too many requests. Please try again in a moment.',
  'api_error': 'Failed to save to Notion. Please try again.',
  'network_error': 'Connection error. Please check your internet.'
};
```

## File Structure Changes

```
aha_catcher/
├── server.py
├── whisper_wrapper.py
├── notion_integration.py      # New: Notion API wrapper
├── config.py                  # New: Configuration management
├── .env                       # Add NOTION_CLIENT_ID, NOTION_CLIENT_SECRET
└── index.html                 # Updated: Add Save button
```

## Dependencies

### Backend
```python
notion-client>=2.0.0  # Official Notion SDK
requests>=2.31.0      # Already installed
cryptography          # For token encryption (optional)
```

### Frontend
- No new dependencies (uses existing Fetch API)

## Configuration

### Environment Variables

```bash
# Notion OAuth (for user authentication)
NOTION_CLIENT_ID=your-client-id
NOTION_CLIENT_SECRET=your-client-secret
NOTION_REDIRECT_URI=http://localhost:8002/api/notion/auth/callback

# Or use Internal Integration Token (simpler, but less flexible)
NOTION_INTEGRATION_TOKEN=secret_xxx  # For single-user/internal use
```

### Notion Setup Steps

1. **Create Notion Integration**
   - Go to https://www.notion.so/my-integrations
   - Click "New integration"
   - Name: "Aha Catcher"
   - Select workspace
   - Copy "Internal Integration Token"

2. **For OAuth (Multi-user)**
   - Create OAuth app at https://www.notion.so/oauth
   - Set redirect URI: `http://localhost:8002/api/notion/auth/callback`
   - Get Client ID and Client Secret

3. **Share Database/Page**
   - Create a page or database in Notion
   - Click "..." → "Connections" → Add integration
   - Select "Aha Catcher" integration

## Implementation Steps

1. ✅ Create plan document (this file)
2. ⏳ Install `notion-client` library
3. ⏳ Create `notion_integration.py` wrapper
4. ⏳ Add Notion endpoints to `server.py`
5. ⏳ Update frontend with Save button
6. ⏳ Implement OAuth flow (or use integration token)
7. ⏳ Test with Notion workspace
8. ⏳ Add error handling
9. ⏳ Add loading states and user feedback
10. ⏳ Update documentation

## Alternative: Simplified MVP (Integration Token)

For faster MVP, skip OAuth and use Internal Integration Token:

**Pros:**
- Faster to implement
- No OAuth complexity
- Good for single-user or internal use

**Cons:**
- Not multi-user friendly
- Requires manual token sharing
- Less secure for production

**Implementation:**
- Store `NOTION_INTEGRATION_TOKEN` in `.env`
- Use token directly (no OAuth flow)
- Simpler code, faster development

## Security Considerations

1. **Token Storage**
   - Never expose tokens in frontend
   - Encrypt tokens in database
   - Use secure session management

2. **OAuth Flow**
   - Use HTTPS in production
   - Validate state parameter
   - Secure redirect URI

3. **API Keys**
   - Store in `.env` file
   - Never commit to version control
   - Rotate keys regularly

## Testing Plan

1. **Unit Tests**
   - Test Notion API wrapper functions
   - Test page creation
   - Test error handling

2. **Integration Tests**
   - Test OAuth flow end-to-end
   - Test save operation
   - Test token refresh

3. **User Testing**
   - Test with real Notion workspace
   - Verify page creation
   - Verify content formatting

## Future Enhancements

1. **Multiple Providers**
   - Google Docs
   - Obsidian (via file system)
   - Evernote
   - OneNote

2. **Advanced Features**
   - Custom page templates
   - Tags/categories
   - Search integration
   - Batch saving

3. **User Preferences**
   - Default save location
   - Auto-save option
   - Format preferences

4. **Database Integration**
   - Store all aha moments in Notion database
   - Query and filter capabilities
   - Analytics and insights

## Cost Considerations

- **Notion API**: Free tier available
- **Rate Limits**: 3 requests per second
- **No additional costs** for basic usage

## Next Steps

1. Start with Internal Integration Token (simplest)
2. Implement basic save functionality
3. Add OAuth later if multi-user support needed
4. Test thoroughly with real Notion workspace
5. Iterate based on user feedback

