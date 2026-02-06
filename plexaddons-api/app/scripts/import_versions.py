"""
Import existing addons from a versions.json file.

This script reads a PlexAddons versions.json file and imports
all addons and versions into the database for the admin user.

Usage:
    python -m app.scripts.import_versions <versions.json> [--admin-discord-id <id>]
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import User, Addon, Version
from app.utils import slugify


async def import_versions(json_path: str, admin_discord_id: str | None = None):
    """Import versions from a JSON file."""
    
    # Read JSON file or URL
    if json_path.startswith('http'):
        async with httpx.AsyncClient() as client:
            response = await client.get(json_path)
            response.raise_for_status()
            data = response.json()
    else:
        with open(json_path, 'r') as f:
            data = json.load(f)
    
    async with AsyncSessionLocal() as db:
        # Find or verify admin user
        if admin_discord_id:
            result = await db.execute(
                select(User).where(User.discord_id == admin_discord_id)
            )
            admin = result.scalar_one_or_none()
            if not admin:
                print(f"Admin user with Discord ID {admin_discord_id} not found")
                return
        else:
            # Find first admin
            result = await db.execute(
                select(User).where(User.is_admin == True).limit(1)
            )
            admin = result.scalar_one_or_none()
            if not admin:
                print("No admin user found. Please create an admin user first.")
                print("Login via Discord first to create your user account.")
                return
        
        print(f"Importing as user: {admin.discord_username} (ID: {admin.id})")
        
        # Handle the PlexAddons format: {"addons": {"AddonName": {...}, ...}}
        addons_data = data.get("addons", {})
        
        # If addons is a dict (PlexAddons format), convert to list
        if isinstance(addons_data, dict):
            addon_list = []
            for addon_name, addon_info in addons_data.items():
                addon_info["name"] = addon_name
                addon_list.append(addon_info)
        else:
            addon_list = addons_data
        
        # Import each addon
        for addon_data in addon_list:
            addon_name = addon_data.get("name")
            if not addon_name:
                continue
            
            slug = slugify(addon_name)
            
            # Check if addon exists
            result = await db.execute(
                select(Addon).where(Addon.slug == slug)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"Addon '{addon_name}' already exists, updating...")
                addon = existing
            else:
                # Create addon
                addon = Addon(
                    owner_id=admin.id,
                    slug=slug,
                    name=addon_name,
                    description=addon_data.get("description"),
                    homepage=addon_data.get("homepage"),
                    external=addon_data.get("external", False),
                    is_active=True,
                    is_public=True,
                )
                db.add(addon)
                await db.flush()
                print(f"Created addon: {addon_name}")
            
            # Check if this addon data has version info at root level (PlexAddons format)
            # vs nested versions array
            if "version" in addon_data:
                # Single version at root level (PlexAddons format)
                versions_list = [addon_data]
            else:
                # Nested versions array
                versions_list = addon_data.get("versions", [])
            
            # Import versions
            for version_data in versions_list:
                version_str = version_data.get("version")
                if not version_str:
                    continue
                
                # Check if version exists
                result = await db.execute(
                    select(Version).where(
                        Version.addon_id == addon.id,
                        Version.version == version_str
                    )
                )
                if result.scalar_one_or_none():
                    print(f"  Version {version_str} already exists, skipping...")
                    continue
                
                # Parse release date
                release_date_str = version_data.get("releaseDate")
                if release_date_str:
                    try:
                        release_date = datetime.fromisoformat(release_date_str.replace('Z', '+00:00'))
                    except:
                        release_date = datetime.now(timezone.utc)
                else:
                    release_date = datetime.now(timezone.utc)
                
                # Create version
                version = Version(
                    addon_id=addon.id,
                    version=version_str,
                    release_date=release_date,
                    download_url=version_data.get("downloadUrl", ""),
                    description=version_data.get("description"),
                    changelog_url=version_data.get("changelogUrl"),
                    changelog_content=version_data.get("changelog"),
                    breaking=version_data.get("breaking", False),
                    urgent=version_data.get("urgent", False),
                    storage_size_bytes=0,
                )
                db.add(version)
                print(f"  Added version: {version_str}")
        
        await db.commit()
        print("\nImport complete!")


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app.scripts.import_versions <versions.json> [--admin-discord-id <id>]")
        sys.exit(1)
    
    json_path = sys.argv[1]
    admin_discord_id = None
    
    if "--admin-discord-id" in sys.argv:
        idx = sys.argv.index("--admin-discord-id")
        if idx + 1 < len(sys.argv):
            admin_discord_id = sys.argv[idx + 1]
    
    asyncio.run(import_versions(json_path, admin_discord_id))


if __name__ == "__main__":
    main()
