# Note Saving Implementation Plan

This document outlines the implementation of Supabase-based note saving for Aha! Catcher.

## Overview

**Goal:** Allow users to save their insights to a database, accessible across devices.

**Architecture:**
```
User saves insight → Your API → Supabase Database
User views history → Your API → Supabase → User's browser
```

**Key Point:** Users never interact with Supabase directly. They use your app, which talks to Supabase behind the scenes.

---

## Phase 1: Supabase Project Setup

### 1.1 Create Supabase Account & Project
1. Go to https://supabase.com
2. Sign up / Sign in (can use GitHub)
3. Click "New Project"
4. Fill in:
   - Organization: Create new or select existing
   - Project name: `aha-catcher`
   - Database password: Generate a strong password (save it!)
   - Region: Select closest to your users (e.g., US East)
5. Click "Create new project" (takes ~2 minutes)

### 1.2 Get API Credentials
1. In Supabase dashboard, go to **Settings** → **API**
2. Note down:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6...` (safe for frontend)
   - **service_role key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6...` (SECRET - backend only!)

### 1.3 Add Environment Variables
Add to Vercel (Settings → Environment Variables):
```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6...  # Only for backend
```

Add to `.env` for local development (this is already added)

Update `.env.example`:
```bash
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

---

## Phase 2: Database Schema Setup

### 2.1 Create Insights Table
In Supabase dashboard, go to **SQL Editor** and run:

```sql
-- Needed for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create insights table
CREATE TABLE insights (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,                    -- Clerk user ID
    transcript TEXT NOT NULL,                  -- Original transcription
    summary TEXT,                              -- AI-generated summary (optional)
    title TEXT,                                -- Auto-generated or user-defined title
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Optional fields for future features
    tags TEXT[] DEFAULT '{}',                  -- Array of tags
    is_favorite BOOLEAN DEFAULT FALSE,
    audio_duration_seconds INTEGER,

    -- Indexes for common queries
    CONSTRAINT insights_user_id_check CHECK (user_id <> '')
);

-- Create index for faster user-based queries
CREATE INDEX insights_user_id_idx ON insights(user_id);
CREATE INDEX insights_created_at_idx ON insights(created_at DESC);

-- NOTE ON SECURITY / RLS:
-- This plan uses SUPABASE_SERVICE_ROLE_KEY in the backend Python API.
-- The service role bypasses Row Level Security (RLS), so RLS policies will NOT be your primary isolation mechanism.
-- Instead, enforce multi-tenancy in your API code by always using `user_id = Clerk sub` on insert,
-- and always filtering queries by `user_id == Clerk sub` on read/update/delete.
--
-- If you later switch to Supabase Auth (or mint Supabase-compatible JWTs), you can enable RLS and use policies.

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to call the function
CREATE TRIGGER update_insights_updated_at
    BEFORE UPDATE ON insights
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2.2 Verify Table Creation
1. Go to **Table Editor** in Supabase dashboard
2. You should see the `insights` table
3. Columns should match the schema above

---

## Phase 3: Backend API Implementation

### 3.1 Install Supabase Python Client
Add to `requirements.txt`:
```
supabase==2.3.0
```

### 3.2 Create Supabase Client Helper
Create `supabase_client.py`:

```python
import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Use service role for backend

_supabase_client: Client = None

def get_supabase() -> Client:
    """Get or create Supabase client instance."""
    global _supabase_client

    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

    return _supabase_client
```

### 3.3 Create Save Insight Endpoint
Create `api/insights_save.py`:

```python
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from clerk_auth import verify_clerk_token
from supabase_client import get_supabase

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InsightSaveRequest(BaseModel):
    transcript: str
    summary: Optional[str] = None
    title: Optional[str] = None
    tags: Optional[List[str]] = []


class InsightResponse(BaseModel):
    id: str
    user_id: str
    transcript: str
    summary: Optional[str]
    title: Optional[str]
    tags: List[str]
    created_at: str
    message: str


@app.post("/api/insights/save")
async def save_insight(
    request: InsightSaveRequest,
    user: dict = Depends(verify_clerk_token)
) -> InsightResponse:
    """Save an insight to Supabase."""
    user_id = user.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    print(f"\n=== SAVE INSIGHT ===")
    print(f"User ID: {user_id}")
    print(f"Transcript length: {len(request.transcript)} chars")
    print(f"Has summary: {bool(request.summary)}")

    try:
        supabase = get_supabase()

        # Generate title from transcript if not provided
        title = request.title
        if not title:
            # Use first 50 chars of transcript as title
            title = request.transcript[:50].strip()
            if len(request.transcript) > 50:
                title += "..."

        # Insert into database
        data = {
            "user_id": user_id,
            "transcript": request.transcript,
            "summary": request.summary,
            "title": title,
            "tags": request.tags or [],
        }

        result = supabase.table("insights").insert(data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to save insight")

        saved = result.data[0]
        print(f"✓ Insight saved with ID: {saved['id']}")

        return InsightResponse(
            id=saved["id"],
            user_id=saved["user_id"],
            transcript=saved["transcript"],
            summary=saved.get("summary"),
            title=saved.get("title"),
            tags=saved.get("tags", []),
            created_at=saved["created_at"],
            message="Insight saved successfully!"
        )

    except Exception as e:
        print(f"✗ Error saving insight: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save: {str(e)}")
```

### 3.4 Create List Insights Endpoint (for future "My Notes" page)
Create `api/insights_list.py`:

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from clerk_auth import verify_clerk_token
from supabase_client import get_supabase

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/insights")
async def list_insights(
    user: dict = Depends(verify_clerk_token),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = None
):
    """List user's insights with pagination and optional search."""
    user_id = user.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    print(f"\n=== LIST INSIGHTS ===")
    print(f"User ID: {user_id}")
    print(f"Limit: {limit}, Offset: {offset}, Search: {search}")

    try:
        supabase = get_supabase()

        # Build query
        query = supabase.table("insights") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1)

        # Add search filter if provided
        if search:
            query = query.or_(f"transcript.ilike.%{search}%,summary.ilike.%{search}%,title.ilike.%{search}%")

        result = query.execute()

        # Get total count for pagination
        count_result = supabase.table("insights") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .execute()

        total_count = count_result.count if count_result.count else 0

        print(f"✓ Found {len(result.data)} insights (total: {total_count})")

        return {
            "insights": result.data,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }

    except Exception as e:
        print(f"✗ Error listing insights: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list insights: {str(e)}")


@app.get("/api/insights/{insight_id}")
async def get_insight(
    insight_id: str,
    user: dict = Depends(verify_clerk_token)
):
    """Get a single insight by ID."""
    user_id = user.get("sub")

    try:
        supabase = get_supabase()

        result = supabase.table("insights") \
            .select("*") \
            .eq("id", insight_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Insight not found")

        return result.data

    except Exception as e:
        print(f"✗ Error getting insight: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get insight: {str(e)}")


@app.delete("/api/insights/{insight_id}")
async def delete_insight(
    insight_id: str,
    user: dict = Depends(verify_clerk_token)
):
    """Delete an insight by ID."""
    user_id = user.get("sub")

    try:
        supabase = get_supabase()

        result = supabase.table("insights") \
            .delete() \
            .eq("id", insight_id) \
            .eq("user_id", user_id) \
            .execute()

        print(f"✓ Deleted insight: {insight_id}")

        return {"success": True, "message": "Insight deleted"}

    except Exception as e:
        print(f"✗ Error deleting insight: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete insight: {str(e)}")
```

### 3.5 Update vercel.json Routes
Add new routes:

```json
{
  "routes": [
    ...existing routes...,
    {
      "src": "/api/insights/save",
      "dest": "/api/insights_save.py"
    },
    {
      "src": "/api/insights",
      "dest": "/api/insights_list.py"
    },
    {
      "src": "/api/insights/(.*)",
      "dest": "/api/insights_list.py"
    }
  ]
}
```

---

## Phase 4: Frontend Integration

### 4.1 Update product.html - Add Save Button Handler
Replace the existing Notion save logic with Supabase save:

```javascript
// Save to Supabase (replaces or supplements Notion save)
async function saveToSupabase() {
    if (!currentTranscription) {
        updateStatus('No transcription available. Please record audio first.', 'error');
        return;
    }

    try {
        saveButton.disabled = true;
        updateStatus('Saving insight...', 'processing');

        const response = await authenticatedFetch('/api/insights/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                transcript: currentTranscription,
                summary: currentSummary || null,
                tags: []  // Can add tag input later
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Failed to save: ${response.status}`);
        }

        const data = await response.json();
        updateStatus('✅ Insight saved!', 'ready');

        // Optional: Show success message with link to "My Notes"
        console.log('Saved insight:', data);

    } catch (error) {
        console.error('Error saving insight:', error);
        updateStatus(`Error: ${error.message}`, 'error');
    } finally {
        saveButton.disabled = false;
    }
}
```

### 4.2 Update Save Button
Change the save button from Notion-specific to generic:

```html
<!-- Change this -->
<button id="saveToNotionButton">💾 Save to Notion</button>

<!-- To this -->
<button id="saveButton">💾 Save Insight</button>
```

---

## Phase 5: Future Enhancements (My Notes Page)

### 5.1 Create My Notes Page
Create `app/notes/page.tsx`:

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';

interface Insight {
  id: string;
  title: string;
  transcript: string;
  summary: string | null;
  created_at: string;
  tags: string[];
}

export default function NotesPage() {
  const { getToken } = useAuth();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchInsights() {
      const token = await getToken();
      const response = await fetch('/api/insights', {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await response.json();
      setInsights(data.insights);
      setLoading(false);
    }
    fetchInsights();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">My Insights</h1>
      {insights.map(insight => (
        <div key={insight.id} className="bg-white p-4 rounded shadow mb-4">
          <h2 className="font-bold">{insight.title}</h2>
          <p className="text-gray-600 text-sm">
            {new Date(insight.created_at).toLocaleDateString()}
          </p>
          <p className="mt-2">{insight.transcript}</p>
          {insight.summary && (
            <div className="mt-2 p-2 bg-gray-50 rounded">
              <strong>Summary:</strong> {insight.summary}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

### 5.2 Add Navigation Link
Update `app/page.tsx` or navigation component:

```tsx
<Link href="/notes">📚 My Notes</Link>
```

---

## Phase 6: Testing Checklist

- [ ] Create Supabase project
- [ ] Run SQL to create `insights` table
- [ ] Add environment variables to Vercel
- [ ] Add environment variables to local `.env`
- [ ] Install `supabase` Python package
- [ ] Create `supabase_client.py`
- [ ] Create `api/insights_save.py`
- [ ] Create `api/insights_list.py`
- [ ] Update `vercel.json` routes
- [ ] Update frontend save button
- [ ] Test saving an insight
- [ ] Verify data appears in Supabase dashboard
- [ ] Test listing insights (for My Notes page)

---

## Environment Variables Summary

```bash
# Existing
OPENAI_API_KEY=...
SUPER_MIND_API_KEY=...
CLERK_SECRET_KEY=...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...

# New for Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6...
```

---

## Security Notes

1. **Service Role Key**: Only use in backend (Python APIs). Never expose to frontend.
2. **Anon Key**: Can be used in frontend, but RLS policies protect data.
3. **Row Level Security**: If you use the service role key, RLS is bypassed—enforce `user_id == Clerk sub` in your API.
4. **Clerk Integration**: User ID from Clerk JWT (`sub`) is used to identify users.
5. **Clerk JWT Verification**: Your backend must verify JWT signatures using Clerk JWKS (recommended: set `CLERK_JWKS_URL`).

---

## Cost Estimate (Supabase Free Tier)

| Resource | Free Tier Limit | Expected Usage |
|----------|-----------------|----------------|
| Database | 500 MB | ~50,000 insights |
| API Requests | Unlimited | ✓ |
| Auth Users | 50,000 MAU | ✓ |
| Storage | 1 GB | N/A (no audio storage) |
| Bandwidth | 2 GB | ✓ |

For a typical user saving 5 insights/day, the free tier should last years.

---

## Future Features (Optional)

1. **Export to Apple Notes** (iOS app)
   - Use iOS Share Sheet
   - Format insight as markdown

2. **Export to Notion** (optional integration)
   - Keep existing Notion OAuth flow
   - Add "Export to Notion" button per insight

3. **Tags & Folders**
   - Add tag input UI
   - Create folders/categories

4. **Search & Filter**
   - Full-text search
   - Date range filter
   - Tag filter

5. **Audio Storage**
   - Store audio files in Supabase Storage
   - Replay recordings
