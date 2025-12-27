# Notion OAuth Implementation Plan

This document outlines the steps to enable multi-user Notion integration, allowing each user to connect their own Notion workspace.

## Current State
- Single internal integration token (`NOTION_INTEGRATION_TOKEN`)
- Only works with the developer's Notion workspace
- All users share the same Notion connection

## Target State
- Each user connects their own Notion account via OAuth
- User tokens stored in Vercel KV (linked to Clerk user ID)
- Users can connect/disconnect their Notion at any time

---

## Phase 1: Notion OAuth App Setup

### 1.1 Create Public Integration
1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Fill in:
   - Name: `Aha! Catcher`
   - Logo: (upload app logo)
   - Associated workspace: Your workspace (for testing)
4. Under "Integration type", select **Public**
5. Add OAuth redirect URI:
   ```
   https://ahacatcher.vercel.app/api/notion/callback
   ```
6. Save and note down:
   - **OAuth client ID**
   - **OAuth client secret**

### 1.2 Add Environment Variables
Add to Vercel (and `.env` for local):
```bash
NOTION_OAUTH_CLIENT_ID=your_oauth_client_id
NOTION_OAUTH_CLIENT_SECRET=your_oauth_client_secret
NOTION_REDIRECT_URI=https://ahacatcher.vercel.app/api/notion/callback
```

---

## Phase 2: Vercel KV Setup

### 2.1 Create Vercel KV Store
1. Go to Vercel Dashboard → Storage → Create Database
2. Select **KV** (Redis-compatible)
3. Name: `aha-catcher-kv`
4. Region: Same as your deployment (iad1 for US East)
5. Click Create

### 2.2 Connect to Project
1. In the KV dashboard, click "Connect to Project"
2. Select `aha_catcher` project
3. This automatically adds environment variables:
   - `KV_URL`
   - `KV_REST_API_URL`
   - `KV_REST_API_TOKEN`
   - `KV_REST_API_READ_ONLY_TOKEN`

### 2.3 Install Python Redis Client
Add to `requirements.txt`:
```
redis==5.0.1
```

---

## Phase 3: Backend OAuth Endpoints

### 3.1 Create `api/notion_connect.py`
Initiates OAuth flow by redirecting to Notion.

```python
import os
from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse
from clerk_auth import verify_clerk_token

app = FastAPI()

NOTION_CLIENT_ID = os.getenv("NOTION_OAUTH_CLIENT_ID")
NOTION_REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI")

@app.get("/api/notion/connect")
async def notion_connect(user: dict = Depends(verify_clerk_token)):
    """Redirect user to Notion OAuth consent page."""
    user_id = user.get("sub")

    # State parameter to prevent CSRF (encode user_id)
    state = user_id  # In production, use encrypted/signed state

    auth_url = (
        f"https://api.notion.com/v1/oauth/authorize"
        f"?client_id={NOTION_CLIENT_ID}"
        f"&response_type=code"
        f"&owner=user"
        f"&redirect_uri={NOTION_REDIRECT_URI}"
        f"&state={state}"
    )

    return RedirectResponse(url=auth_url)
```

### 3.2 Create `api/notion_callback.py`
Handles OAuth callback, exchanges code for token, stores in KV.

```python
import os
import requests
import redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

app = FastAPI()

NOTION_CLIENT_ID = os.getenv("NOTION_OAUTH_CLIENT_ID")
NOTION_CLIENT_SECRET = os.getenv("NOTION_OAUTH_CLIENT_SECRET")
NOTION_REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI")
KV_URL = os.getenv("KV_URL")

# Connect to Vercel KV
kv = redis.from_url(KV_URL)

@app.get("/api/notion/callback")
async def notion_callback(code: str, state: str):
    """Handle Notion OAuth callback."""
    user_id = state  # The Clerk user ID passed in state

    # Exchange code for access token
    response = requests.post(
        "https://api.notion.com/v1/oauth/token",
        auth=(NOTION_CLIENT_ID, NOTION_CLIENT_SECRET),
        json={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": NOTION_REDIRECT_URI
        },
        headers={"Content-Type": "application/json"}
    )

    if not response.ok:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")

    data = response.json()
    access_token = data["access_token"]
    workspace_name = data.get("workspace_name", "Unknown")
    workspace_id = data.get("workspace_id", "")

    # Store token in Vercel KV
    # Key: notion_token:{user_id}
    # Value: JSON with token and metadata
    import json
    kv.set(
        f"notion_token:{user_id}",
        json.dumps({
            "access_token": access_token,
            "workspace_name": workspace_name,
            "workspace_id": workspace_id
        })
    )

    # Redirect back to app with success message
    return RedirectResponse(url="/product?notion=connected")
```

### 3.3 Create `api/notion_disconnect.py`
Removes user's Notion connection.

```python
import os
import redis
from fastapi import FastAPI, Depends
from clerk_auth import verify_clerk_token

app = FastAPI()

KV_URL = os.getenv("KV_URL")
kv = redis.from_url(KV_URL)

@app.post("/api/notion/disconnect")
async def notion_disconnect(user: dict = Depends(verify_clerk_token)):
    """Remove user's Notion connection."""
    user_id = user.get("sub")

    # Delete token from KV
    kv.delete(f"notion_token:{user_id}")

    return {"success": True, "message": "Notion disconnected"}
```

### 3.4 Update `api/notion_status.py`
Check if user has connected Notion.

```python
import os
import json
import redis
from fastapi import FastAPI, Depends
from clerk_auth import verify_clerk_token

app = FastAPI()

KV_URL = os.getenv("KV_URL")
kv = redis.from_url(KV_URL)

@app.get("/api/notion/status")
async def notion_status(user: dict = Depends(verify_clerk_token)):
    """Check if user has connected Notion."""
    user_id = user.get("sub")

    # Check for user's token in KV
    token_data = kv.get(f"notion_token:{user_id}")

    if token_data:
        data = json.loads(token_data)
        return {
            "connected": True,
            "workspace_name": data.get("workspace_name", "Connected"),
            "message": f"Connected to {data.get('workspace_name', 'Notion')}"
        }
    else:
        return {
            "connected": False,
            "message": "Notion not connected. Click 'Connect Notion' to get started."
        }
```

### 3.5 Update `api/notion_save.py`
Use user's token instead of global token.

```python
# Add to notion_save.py

import redis
import json

KV_URL = os.getenv("KV_URL")
kv = redis.from_url(KV_URL)

def get_user_notion_token(user_id: str) -> str:
    """Get user's Notion access token from KV."""
    token_data = kv.get(f"notion_token:{user_id}")
    if not token_data:
        return None
    data = json.loads(token_data)
    return data.get("access_token")

# In the save endpoint:
@app.post("/api/notion/save")
async def save_to_notion(request: NotionSaveRequest, user: dict = Depends(verify_clerk_token)):
    user_id = user.get("sub")

    # Get user's Notion token
    access_token = get_user_notion_token(user_id)
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Notion not connected. Please connect your Notion account first."
        )

    # Use this token for Notion API calls
    notion = NotionIntegration(token=access_token)
    # ... rest of save logic
```

---

## Phase 4: Update vercel.json Routes

Add new routes:
```json
{
  "routes": [
    ...existing routes...,
    {
      "src": "/api/notion/connect",
      "dest": "/api/notion_connect.py"
    },
    {
      "src": "/api/notion/callback",
      "dest": "/api/notion_callback.py"
    },
    {
      "src": "/api/notion/disconnect",
      "dest": "/api/notion_disconnect.py"
    }
  ]
}
```

---

## Phase 5: Frontend UI Updates

### 5.1 Update `product.html`

Add Notion connection UI:

```html
<!-- Add after the save button -->
<div id="notionConnectionSection" class="notion-connection">
    <div id="notionNotConnected" style="display: none;">
        <p>Connect your Notion to save insights</p>
        <button id="connectNotionButton" onclick="connectNotion()">
            🔗 Connect Notion
        </button>
    </div>
    <div id="notionConnected" style="display: none;">
        <p>✓ Connected to <span id="workspaceName"></span></p>
        <button id="disconnectNotionButton" onclick="disconnectNotion()">
            Disconnect
        </button>
    </div>
</div>
```

### 5.2 Add JavaScript Functions

```javascript
// Check Notion connection status on load
async function checkNotionConnection() {
    try {
        const response = await authenticatedFetch('/api/notion/status');
        const data = await response.json();

        if (data.connected) {
            document.getElementById('notionNotConnected').style.display = 'none';
            document.getElementById('notionConnected').style.display = 'block';
            document.getElementById('workspaceName').textContent = data.workspace_name;
            document.getElementById('saveToNotionButton').disabled = false;
        } else {
            document.getElementById('notionNotConnected').style.display = 'block';
            document.getElementById('notionConnected').style.display = 'none';
            document.getElementById('saveToNotionButton').disabled = true;
        }
    } catch (error) {
        console.error('Error checking Notion status:', error);
    }
}

// Redirect to Notion OAuth
function connectNotion() {
    // Store current page to return after OAuth
    sessionStorage.setItem('notion_return_url', window.location.href);

    // Get auth token and pass to connect endpoint
    const token = getClerkToken();
    window.location.href = `/api/notion/connect?token=${token}`;
}

// Disconnect Notion
async function disconnectNotion() {
    if (!confirm('Disconnect your Notion account?')) return;

    try {
        await authenticatedFetch('/api/notion/disconnect', { method: 'POST' });
        checkNotionConnection();
    } catch (error) {
        console.error('Error disconnecting Notion:', error);
    }
}

// Check on page load
window.addEventListener('load', () => {
    checkNotionConnection();

    // Check for OAuth callback
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('notion') === 'connected') {
        alert('Notion connected successfully!');
        // Clean up URL
        window.history.replaceState({}, '', '/product');
    }
});
```

---

## Phase 6: Update NotionIntegration Class

Modify `notion_integration.py` to accept token as parameter:

```python
class NotionIntegration:
    def __init__(self, token: str = None):
        """Initialize with user's token or fall back to env var."""
        self.token = token or os.getenv("NOTION_INTEGRATION_TOKEN")
        if not self.token:
            raise ValueError("Notion token not provided")

        self.client = Client(auth=self.token)
```

---

## Phase 7: Testing Checklist

- [ ] Create Notion Public Integration
- [ ] Set up Vercel KV store
- [ ] Add all environment variables to Vercel
- [ ] Deploy and test OAuth flow:
  - [ ] Click "Connect Notion"
  - [ ] Authorize on Notion
  - [ ] Redirected back to app
  - [ ] Status shows "Connected to [workspace]"
- [ ] Test saving to user's Notion
- [ ] Test disconnect flow
- [ ] Test with multiple users

---

## Security Considerations

1. **State Parameter**: Currently using plain user_id. For production, encrypt/sign it to prevent CSRF.

2. **Token Storage**: Vercel KV encrypts data at rest. Consider adding expiration for tokens.

3. **Scope Limitations**: OAuth tokens only have access to pages user explicitly shares with the integration.

4. **Error Handling**: Add proper error messages for OAuth failures (user denied, invalid code, etc.)

---

## Environment Variables Summary

```bash
# Existing
OPENAI_API_KEY=...
SUPER_MIND_API_KEY=...
CLERK_SECRET_KEY=...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...

# New for Notion OAuth
NOTION_OAUTH_CLIENT_ID=...
NOTION_OAUTH_CLIENT_SECRET=...
NOTION_REDIRECT_URI=https://ahacatcher.vercel.app/api/notion/callback

# Auto-added by Vercel KV
KV_URL=...
KV_REST_API_URL=...
KV_REST_API_TOKEN=...
KV_REST_API_READ_ONLY_TOKEN=...
```

---

## Estimated Implementation Time

| Phase | Description | Complexity |
|-------|-------------|------------|
| 1 | Notion OAuth App Setup | Simple |
| 2 | Vercel KV Setup | Simple |
| 3 | Backend OAuth Endpoints | Medium |
| 4 | Update Routes | Simple |
| 5 | Frontend UI Updates | Medium |
| 6 | NotionIntegration Updates | Simple |
| 7 | Testing | Medium |
