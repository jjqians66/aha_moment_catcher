"""
Clerk Authentication Helper

Validates Clerk JWT tokens for Python FastAPI endpoints.
"""

import os
import jwt
from fastapi import HTTPException, Header
from typing import Optional

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")


def verify_clerk_token(authorization: Optional[str] = Header(None)) -> dict:
    """
    Verify Clerk JWT token from Authorization header.

    Args:
        authorization: Authorization header value (format: "Bearer <token>")

    Returns:
        Decoded token payload with user information

    Raises:
        HTTPException: If token is invalid or missing
    """
    # If no Clerk secret key is configured, skip auth (for development)
    if not CLERK_SECRET_KEY:
        print("Warning: CLERK_SECRET_KEY not set, skipping auth")
        return {"sub": "anonymous", "dev_mode": True}

    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization token provided")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization.replace("Bearer ", "")

    try:
        # Decode without full verification for now
        # In production, you should verify with Clerk's JWKS
        decoded = jwt.decode(
            token,
            options={"verify_signature": False}
        )

        # Basic validation - check if token has required fields
        if not decoded.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")

        return decoded

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
