import logging
from functools import lru_cache

import jwt as pyjwt
from config import get_settings
from edu_core.schemas.users import UserDto
from edu_core.moderation import (
    UNVERIFIED_MESSAGE,
    ban_message,
    is_banned,
    is_verified,
)
from edu_core.services import UserService
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)


# Public keys for Google Identity Platform / Firebase Authentication ID tokens
FIREBASE_JWKS_URL = (
    "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
)


@lru_cache
def _jwks_client(jwks_url: str) -> pyjwt.PyJWKClient:
    """JWKS client for asymmetric JWT signing keys (keys are cached)."""
    return pyjwt.PyJWKClient(jwks_url, lifespan=3600)


def _decode_firebase_token(token: str, project_id: str) -> dict:
    """Verify an Identity Platform (Firebase Auth) ID token for this project."""
    signing_key = _jwks_client(FIREBASE_JWKS_URL).get_signing_key_from_jwt(token)
    return pyjwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=project_id,
        issuer=f"https://securetoken.google.com/{project_id}",
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> UserDto:
    """
    Get the current authenticated user from the login token (Google Identity
    Platform when FIREBASE_PROJECT_ID is set, otherwise Supabase).

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        UserDto: The authenticated user

    Raises:
        HTTPException: If authentication fails or user not found
    """
    settings = get_settings()
    supabase_jwt_secret = settings.supabase_jwt_secret

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # For debugging: Peek at the header without verification
        try:
            unverified_header = pyjwt.get_unverified_header(token)
            alg = unverified_header.get("alg")
        except Exception:
            alg = "HS256"
            print("Could not peek at token header")

        if settings.firebase_project_id:
            # Google Identity Platform (production)
            payload = _decode_firebase_token(token, settings.firebase_project_id)
        elif alg.startswith("HS"):
            # Symmetric verification (legacy Supabase JWT secret)
            if not supabase_jwt_secret:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Supabase JWT secret not configured",
                )
            payload = pyjwt.decode(
                token,
                supabase_jwt_secret,
                algorithms=["HS256", "HS384", "HS512"],
                options={"verify_aud": False},
            )
        else:
            # Asymmetric verification using JWKS
            supabase_url = settings.supabase_url
            if not supabase_url:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="SUPABASE_URL must be configured for asymmetric JWT verification",
                )

            # Use JWKS to fetch public keys (client caches them between requests)
            signing_key = _jwks_client(
                f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            ).get_signing_key_from_jwt(token)

            payload = pyjwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                options={"verify_aud": False},
            )

        # Extract Supabase user ID (sub claim) - this is the UUID from auth.users
        supabase_user_id = payload.get("sub")
        if not supabase_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )

        # Extract user information from token
        email = payload.get("email")
        # Supabase tokens carry the name in user_metadata; Firebase tokens in "name"
        user_metadata = payload.get("user_metadata", {})

        # Get name from the token or fall back to the email
        name = (
            payload.get("name")
            or user_metadata.get("name")
            or user_metadata.get("full_name")
        )
        if not name and email:
            # Fallback to email username part
            name = email.split("@")[0]

        # Use UserService to get or create user (doesn't expose DB directly)
        user_service = UserService()

        # A token proves somebody typed a password, not that the address is
        # real. Google issues one for anything@anywhere, so a made-up address
        # became a working account with its own daily quota, and a copied
        # front end could mint them in a loop. The token says which of the two
        # happened; this reads it.
        #
        # Only new accounts are asked. Anyone already studying here keeps
        # working whatever their token says - requiring it of them would lock
        # out a class mid-week for something nobody told them to do.
        if not is_verified(payload) and not user_service.exists(supabase_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=UNVERIFIED_MESSAGE,
            )

        user_dto = user_service.get_or_create_user_from_token(
            user_id=supabase_user_id,
            email=email,
            name=name,
        )

        # A suspended account is turned away here, at the one point every
        # signed-in request passes through. Checking it in each router would
        # mean a banned student kept whichever endpoint somebody forgot.
        #
        # 403 and not 401: the token is perfectly valid, so the client must
        # not treat this as an expired session and try to refresh it in a
        # loop. The message says when it lifts, because an account that stops
        # working with no explanation reads as a broken app.
        if is_banned(user_dto.banned_at, user_dto.banned_until):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ban_message(user_dto.banned_until, user_dto.ban_reason),
            )

        return user_dto

    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except pyjwt.InvalidTokenError as e:
        # The reason stays in the log, not in the reply. The library's own
        # wording describes its internals - which library it is, how far it
        # parsed, which byte stopped it - and a caller holding a rejected
        # token learns only that it was rejected. Expiry is told apart above,
        # because that one is actionable: refresh and try again.
        logger.warning("Rejected a token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    except HTTPException:
        raise
    except Exception:
        # logger.exception already records the traceback, so the exception
        # does not need binding.
        logger.exception("Authentication failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> UserDto | None:
    """
    Get the current user if authenticated, otherwise return None.
    Useful for endpoints that work with or without authentication.
    """
    if not credentials:
        return None

    settings = get_settings()
    jwt_secret = settings.supabase_jwt_secret
    if not jwt_secret:
        return None

    try:
        return get_current_user(credentials)
    except HTTPException:
        return None
