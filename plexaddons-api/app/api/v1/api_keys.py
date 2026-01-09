"""
API Key Management Endpoints

Allows users to create, manage, and revoke API keys with granular permissions.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models import User, ApiKeyScope
from app.schemas import (
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
    ApiKeyListResponse,
    AvailableScopesResponse,
    ApiKeyScopeInfo,
)
from app.services.api_key_service import ApiKeyService, MAX_KEYS_PER_TIER
from app.api.deps import get_effective_tier

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# Scope descriptions for documentation
SCOPE_INFO = {
    ApiKeyScope.ADDONS_READ: {
        "name": "Read Addons",
        "description": "View addon information and metadata",
        "min_tier": "pro"
    },
    ApiKeyScope.VERSIONS_READ: {
        "name": "Read Versions", 
        "description": "View version information and changelogs",
        "min_tier": "pro"
    },
    ApiKeyScope.ANALYTICS_READ: {
        "name": "Read Analytics",
        "description": "Access download and usage analytics",
        "min_tier": "pro"
    },
    ApiKeyScope.VERSIONS_WRITE: {
        "name": "Publish Versions",
        "description": "Publish new addon versions (CI/CD)",
        "min_tier": "premium"
    },
    ApiKeyScope.ADDONS_WRITE: {
        "name": "Manage Addons",
        "description": "Create and update addon settings",
        "min_tier": "premium"
    },
    ApiKeyScope.WEBHOOKS_MANAGE: {
        "name": "Manage Webhooks",
        "description": "Create, update, and delete webhooks",
        "min_tier": "premium"
    },
    ApiKeyScope.FULL_ACCESS: {
        "name": "Full Access",
        "description": "Complete API access (all permissions)",
        "min_tier": "premium"
    },
}


@router.get("/scopes", response_model=AvailableScopesResponse)
async def get_available_scopes(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Get available API key scopes for the current user's tier.
    
    Returns the list of scopes the user can assign to their API keys,
    based on their subscription tier.
    """
    available_scopes = ApiKeyService.get_available_scopes(current_user)
    effective_tier = get_effective_tier(current_user)
    max_keys = MAX_KEYS_PER_TIER.get(effective_tier, 0)
    
    scope_info_list = []
    for scope in available_scopes:
        info = SCOPE_INFO.get(scope, {
            "name": scope.value,
            "description": "No description available",
            "min_tier": "premium"
        })
        scope_info_list.append(ApiKeyScopeInfo(
            scope=scope.value,
            name=info["name"],
            description=info["description"],
            min_tier=info["min_tier"]
        ))
    
    return AvailableScopesResponse(
        scopes=scope_info_list,
        tier=effective_tier.value,
        max_keys=max_keys
    )


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    List all API keys for the current user.
    
    Returns key metadata but never the actual key values.
    """
    keys = await ApiKeyService.get_user_keys(db, current_user.id)
    effective_tier = get_effective_tier(current_user)
    max_keys = MAX_KEYS_PER_TIER.get(effective_tier, 0)
    
    return ApiKeyListResponse(
        keys=[ApiKeyResponse.model_validate(k) for k in keys],
        count=len(keys),
        max_keys=max_keys
    )


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Create a new API key.
    
    **Important**: The API key value is only shown once in this response!
    Make sure to save it securely.
    
    Scopes must be valid for your subscription tier:
    - **Pro**: addons:read, versions:read, analytics:read
    - **Premium**: All scopes including write permissions
    """
    # Create the key (service handles all validation)
    api_key_obj, full_key = await ApiKeyService.create_key(
        db=db,
        user=current_user,
        name=data.name,
        scopes=data.scopes,
        expires_at=data.expires_at
    )
    
    return ApiKeyCreatedResponse(
        key=ApiKeyResponse.model_validate(api_key_obj),
        api_key=full_key
    )


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """Get details of a specific API key."""
    key = await ApiKeyService.get_key_by_id(db, key_id, current_user.id)
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return ApiKeyResponse.model_validate(key)


@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: int,
    data: ApiKeyUpdate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Update an API key's name, scopes, or expiration.
    
    Note: You cannot change scopes to ones not allowed by your tier.
    """
    key = await ApiKeyService.get_key_by_id(db, key_id, current_user.id)
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Update (service handles scope validation)
    updated = await ApiKeyService.update_key(
        db=db,
        api_key=key,
        user=current_user,
        name=data.name,
        scopes=data.scopes,
        expires_at=data.expires_at
    )
    
    return ApiKeyResponse.model_validate(updated)


@router.post("/{key_id}/revoke", response_model=ApiKeyResponse)
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Revoke an API key (deactivate without deleting).
    
    A revoked key will no longer work but its history is preserved.
    """
    key = await ApiKeyService.get_key_by_id(db, key_id, current_user.id)
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    revoked = await ApiKeyService.revoke_key(db, key)
    return ApiKeyResponse.model_validate(revoked)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Permanently delete an API key.
    
    This cannot be undone. If you just want to disable the key,
    use the revoke endpoint instead.
    """
    key = await ApiKeyService.get_key_by_id(db, key_id, current_user.id)
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    await ApiKeyService.delete_key(db, key)
