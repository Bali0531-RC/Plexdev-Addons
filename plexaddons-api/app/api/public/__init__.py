from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.database import get_db
from app.services import AddonService
from app.schemas import PublicVersionsJson, PublicAddonVersion
from app.api.deps import rate_limit_check

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
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
):
    """Get latest version info for a specific addon by name."""
    from app.core.exceptions import NotFoundError
    
    addon_data = await AddonService.get_all_public_addons_for_json(db)
    
    for addon in addon_data:
        if addon["name"].lower() == name.lower():
            return addon
    
    raise NotFoundError(f"Addon '{name}' not found")
