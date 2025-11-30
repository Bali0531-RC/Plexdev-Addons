from fastapi import APIRouter, Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional
from app.database import get_db
from app.services import AddonService, AnalyticsService
from app.schemas import PublicVersionsJson, PublicAddonVersion
from app.api.deps import rate_limit_check
from app.models import Addon, Version

router = APIRouter(tags=["Public API"])


@router.get("/versions.json", response_model=PublicVersionsJson)
async def get_versions_json(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
):
    """
    Get versions.json - backward compatible with existing VersionChecker.js clients.
    
    This endpoint returns all public addons with their latest version info
    in the same format as the original GitHub-hosted versions.json.
    """
    addon_data = await AddonService.get_all_public_addons_for_json(db)
    
    addons_dict = {}
    for addon in addon_data:
        addons_dict[addon["name"]] = PublicAddonVersion(
            version=addon["version"],
            releaseDate=addon["release_date"],
            downloadUrl=addon["download_url"],
            description=addon["description"],
            breaking=addon["breaking"],
            urgent=addon["urgent"],
            external=addon["external"],
            author=addon["author"],
            homepage=addon["homepage"],
            changelog=addon["changelog"],
        )
    
    return PublicVersionsJson(
        addons=addons_dict,
        lastUpdated=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        repository="https://github.com/Bali0531-RC/PlexAddons",
        supportContact="https://discord.com/users/yourDiscordId",
    )


@router.get("/api/addons")
async def public_addon_list(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
):
    """Get public addon list with basic info."""
    addon_data = await AddonService.get_all_public_addons_for_json(db)
    return {"addons": addon_data, "count": len(addon_data)}


@router.get("/api/addons/{name}/latest")
async def public_addon_latest(
    name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
    x_current_version: Optional[str] = Header(None, alias="X-Current-Version"),
):
    """
    Get latest version info for a specific addon by name.
    
    Optional X-Current-Version header:
    - If provided, the version will be logged for analytics
    - This allows addon owners to see which versions their users are running
    """
    from app.core.exceptions import NotFoundError
    
    addon_data = await AddonService.get_all_public_addons_for_json(db)
    
    for addon in addon_data:
        if addon["name"].lower() == name.lower():
            # Log version check for analytics if version header provided
            if x_current_version:
                try:
                    # Get client IP
                    client_ip = request.client.host if request.client else "unknown"
                    
                    # Find addon and version in database
                    addon_result = await db.execute(
                        select(Addon).where(Addon.name == addon["name"])
                    )
                    db_addon = addon_result.scalar_one_or_none()
                    
                    if db_addon:
                        # Find the version if it exists
                        version_result = await db.execute(
                            select(Version).where(
                                Version.addon_id == db_addon.id,
                                Version.version == x_current_version
                            )
                        )
                        version = version_result.scalar_one_or_none()
                        version_id = version.id if version else None
                        
                        # Log the version check
                        await AnalyticsService.log_version_check(
                            db,
                            addon_id=db_addon.id,
                            version_id=version_id,
                            checked_version=x_current_version,
                            client_ip=client_ip,
                        )
                        
                        # Update daily stats
                        ip_hash = AnalyticsService.hash_ip(client_ip)
                        await AnalyticsService.update_daily_stats(
                            db,
                            addon_id=db_addon.id,
                            version_id=version_id,
                            client_ip_hash=ip_hash,
                        )
                except Exception as e:
                    # Don't fail the request if analytics logging fails
                    print(f"Analytics logging error: {e}")
            
            return addon
    
    raise NotFoundError(f"Addon '{name}' not found")
