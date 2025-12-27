"""
Clerk Authentication Helper

Validates Clerk JWT tokens for Python FastAPI endpoints.
"""

import os
import jwt
from fastapi import HTTPException, Header
from typing import Optional
from jwt import PyJWKClient

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")
CLERK_ISSUER = os.getenv("CLERK_ISSUER")
CLERK_AUDIENCE = os.getenv("CLERK_AUDIENCE")

_jwk_client: Optional[PyJWKClient] = None


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        if not CLERK_JWKS_URL:
            raise ValueError("CLERK_JWKS_URL must be set to verify Clerk JWT signatures")
        _jwk_client = PyJWKClient(CLERK_JWKS_URL)
    return _jwk_client


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
        if CLERK_JWKS_URL:
            jwk_client = _get_jwk_client()
            signing_key = jwk_client.get_signing_key_from_jwt(token).key

            # Only verify issuer/audience if configured (keeps local setup simple).
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": bool(CLERK_AUDIENCE),
                "verify_iss": bool(CLERK_ISSUER),
            }

            decoded = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=CLERK_AUDIENCE,
                issuer=CLERK_ISSUER,
                options=options,
            )
            decoded["_signature_verified"] = True
        else:
            # WARNING: This is insecure. Use only for local development.
            decoded = jwt.decode(token, options={"verify_signature": False})
            decoded["_signature_verified"] = False

        # Basic validation - check if token has required fields
        if not decoded.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")

        return decoded

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
