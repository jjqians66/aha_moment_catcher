"""
Notion Integration Wrapper

This module provides a wrapper for saving aha moments to Notion
using the Internal Integration Token approach (simpler MVP).
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from notion_client import Client, APIErrorCode, APIResponseError


class NotionIntegration:
    """
    Wrapper class for Notion API integration.
    
    Uses Internal Integration Token for authentication.
    Creates formatted pages in Notion with aha moment content.
    """
    
    def __init__(self, integration_token: Optional[str] = None):
        """
        Initialize the Notion integration.
        
        Args:
            integration_token: Notion Internal Integration Token.
                            If None, will try to get from NOTION_INTEGRATION_TOKEN env var.
        """
        self.integration_token = integration_token or os.getenv("NOTION_INTEGRATION_TOKEN")
        if not self.integration_token:
            raise ValueError(
                "Notion integration token not provided. "
                "Set NOTION_INTEGRATION_TOKEN environment variable or pass integration_token parameter."
            )
        
        self.client = Client(auth=self.integration_token)
    
    def _format_page_id(self, page_id: str) -> str:
        """
        Format a Notion page ID to UUID format if needed.

        Args:
            page_id: Raw page ID (with or without dashes)

        Returns:
            Formatted UUID string
        """
        # Remove all dashes and spaces
        clean_id = page_id.replace('-', '').replace(' ', '').strip()

        # If it's 32 characters (hex UUID without dashes), format it
        if len(clean_id) == 32:
            return f"{clean_id[0:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:32]}"

        # Otherwise return as-is (already formatted or invalid)
        return page_id.strip()

    def create_aha_page(
        self,
        parent_page_id: str,
        transcript: str,
        summary: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Notion page with aha moment content.

        Args:
            parent_page_id: ID of the parent page/database where to create the page
            transcript: Transcription text
            summary: Research summary text (optional)
            timestamp: ISO format timestamp (optional, defaults to current time)

        Returns:
            Dictionary with created page information including page URL

        Raises:
            ValueError: If parent_page_id is invalid or page creation fails
            APIResponseError: If Notion API returns an error
        """
        if not transcript or not transcript.strip():
            raise ValueError("Transcript cannot be empty")

        if not parent_page_id:
            raise ValueError("Parent page ID is required")

        # Format the page ID to ensure it has dashes
        parent_page_id = self._format_page_id(parent_page_id)
        
        # Use current timestamp if not provided
        if not timestamp:
            timestamp = datetime.now().isoformat()
        
        # Format timestamp for display
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            formatted_timestamp = timestamp
        
        # Build page content blocks
        blocks = []
        
        # Title block
        blocks.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": f"💡 Aha Moment - {formatted_timestamp}"}
                    }
                ]
            }
        })
        
        # Timestamp block
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": f"📅 Captured: {formatted_timestamp}"}
                    }
                ]
            }
        })
        
        # Divider
        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })
        
        # Transcription section
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": "📝 Transcription"}
                    }
                ]
            }
        })
        
        # Split transcript into paragraphs if it's long
        transcript_paragraphs = transcript.split('\n\n') if '\n\n' in transcript else [transcript]
        for para in transcript_paragraphs:
            if para.strip():
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": para.strip()}
                            }
                        ]
                    }
                })
        
        # Research Summary section
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": "🔍 Research Summary"}
                    }
                ]
            }
        })
        
        if summary and summary.strip():
            # Split summary into paragraphs
            summary_paragraphs = summary.split('\n\n') if '\n\n' in summary else [summary]
            for para in summary_paragraphs:
                if para.strip():
                    # Check if it's a markdown header
                    if para.strip().startswith('#'):
                        level = len(para) - len(para.lstrip('#'))
                        content = para.strip().lstrip('#').strip()
                        heading_type = f"heading_{min(level, 3)}"
                        blocks.append({
                            "object": "block",
                            "type": heading_type,
                            heading_type: {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {"content": content}
                                    }
                                ]
                            }
                        })
                    else:
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {"content": para.strip()}
                                    }
                                ]
                            }
                        })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "Not generated"},
                            "annotations": {"italic": True}
                        }
                    ]
                }
            })
        
        try:
            # Create the page
            page = self.client.pages.create(
                parent={"page_id": parent_page_id},
                properties={
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": f"Aha Moment - {formatted_timestamp}"
                                }
                            }
                        ]
                    }
                },
                children=blocks
            )
            
            # Get page URL
            page_url = page.get("url", "")
            if page_url and not page_url.startswith("http"):
                page_url = f"https://notion.so/{page_url.replace('-', '')}"
            
            return {
                "success": True,
                "page_id": page.get("id"),
                "page_url": page_url,
                "created_time": page.get("created_time")
            }
            
        except APIResponseError as e:
            if e.code == APIErrorCode.ObjectNotFound:
                raise ValueError(f"Parent page not found. Please check the parent_page_id: {parent_page_id}")
            elif e.code == APIErrorCode.Unauthorized:
                raise ValueError("Invalid Notion integration token. Please check your NOTION_INTEGRATION_TOKEN.")
            elif e.code == APIErrorCode.RateLimited:
                raise RuntimeError("Notion API rate limit exceeded. Please try again in a moment.")
            else:
                raise RuntimeError(f"Notion API error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to create Notion page: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        Test the connection to Notion API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to list users (lightweight operation)
            self.client.users.list()
            return True
        except Exception:
            return False


# Global instance (lazy initialization)
_notion_instance: Optional[NotionIntegration] = None


def get_notion_integration() -> NotionIntegration:
    """
    Get or create the global NotionIntegration instance.
    
    Returns:
        NotionIntegration instance
    
    Raises:
        ValueError: If NOTION_INTEGRATION_TOKEN is not set
    """
    global _notion_instance
    if _notion_instance is None:
        _notion_instance = NotionIntegration()
    return _notion_instance



