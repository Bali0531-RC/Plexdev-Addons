"""Automated changelog generation service.

Generates changelogs from version history, comparing adjacent versions
and producing formatted Markdown output.
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Version, Addon


class ChangelogService:
    """Generate changelogs from addon version history."""

    @staticmethod
    async def generate_changelog(
        db: AsyncSession,
        addon_id: int,
        from_version: Optional[str] = None,
        to_version: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """
        Generate a Markdown changelog for an addon.

        If from_version/to_version are provided, only include versions in that range.
        Otherwise, include the latest `limit` versions.
        """
        query = (
            select(Version)
            .where(Version.addon_id == addon_id, Version.is_published == True)
            .order_by(Version.created_at.desc())
        )

        if from_version and to_version:
            # Get versions between the two semvers (inclusive)
            from_row = await db.execute(
                select(Version.created_at)
                .where(Version.addon_id == addon_id, Version.version == from_version)
            )
            to_row = await db.execute(
                select(Version.created_at)
                .where(Version.addon_id == addon_id, Version.version == to_version)
            )
            from_ts = from_row.scalar_one_or_none()
            to_ts = to_row.scalar_one_or_none()

            if from_ts and to_ts:
                low, high = sorted([from_ts, to_ts])
                query = query.where(
                    Version.created_at >= low,
                    Version.created_at <= high,
                )
        else:
            query = query.limit(limit)

        result = await db.execute(query)
        versions = result.scalars().all()

        if not versions:
            return "# Changelog\n\nNo versions found.\n"

        # Fetch addon name
        addon_result = await db.execute(select(Addon.name).where(Addon.id == addon_id))
        addon_name = addon_result.scalar_one_or_none() or "Addon"

        return ChangelogService._format_changelog(addon_name, versions)

    @staticmethod
    def _format_changelog(addon_name: str, versions: list) -> str:
        """Format versions into a Markdown changelog."""
        lines = [f"# {addon_name} — Changelog\n"]

        for v in versions:
            # Version header with date
            date_str = ""
            if v.release_date:
                date_str = v.release_date.isoformat()
            elif v.created_at:
                date_str = v.created_at.strftime("%Y-%m-%d")

            flags = []
            if v.breaking:
                flags.append("**BREAKING**")
            if v.urgent:
                flags.append("**URGENT**")
            if v.is_deprecated:
                flags.append("~~deprecated~~")
            if v.channel and v.channel.value != "stable":
                flags.append(f"`{v.channel.value}`")

            flag_str = " ".join(flags)
            header = f"## [{v.version}] — {date_str}"
            if flag_str:
                header += f"  {flag_str}"
            lines.append(header)
            lines.append("")

            # Description
            if v.description:
                lines.append(v.description)
                lines.append("")

            # Changelog content
            if v.changelog_content:
                lines.append(v.changelog_content)
                lines.append("")

            # Deprecation notice
            if v.is_deprecated and v.deprecation_reason:
                lines.append(f"> **Deprecated:** {v.deprecation_reason}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)
