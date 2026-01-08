"""Analytics service for version check tracking and usage statistics."""

import hashlib
from datetime import date, datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models import (
    VersionCheck, AddonUsageStats, Addon, Version, User, SubscriptionTier
)
from app.schemas import (
    AddonAnalyticsResponse, DailyStats, VersionDistribution, AnalyticsSummary
)


class AnalyticsService:
    """Service for tracking and retrieving addon usage analytics."""
    
    @staticmethod
    def hash_ip(ip_address: str) -> str:
        """Hash an IP address for privacy-preserving unique user tracking."""
        # Use SHA256 with a static salt for consistent user tracking across days
        # This allows identifying returning users while preserving privacy
        salted = f"{ip_address}:plexaddons-v2-salt"
        return hashlib.sha256(salted.encode()).hexdigest()[:32]
    
    @staticmethod
    async def log_version_check(
        db: AsyncSession,
        addon_id: int,
        version_id: Optional[int],
        checked_version: str,
        client_ip: str,
    ) -> VersionCheck:
        """
        Log a version check request.
        
        Args:
            addon_id: The addon being checked
            version_id: The version ID if resolved, None if version not found
            checked_version: The version string provided by the client
            client_ip: Client IP address (will be hashed)
        """
        ip_hash = AnalyticsService.hash_ip(client_ip)
        
        check = VersionCheck(
            addon_id=addon_id,
            version_id=version_id,
            checked_version=checked_version,
            client_ip_hash=ip_hash,
        )
        db.add(check)
        await db.commit()
        await db.refresh(check)
        
        return check
    
    @staticmethod
    async def update_daily_stats(
        db: AsyncSession,
        addon_id: int,
        version_id: Optional[int],
        client_ip_hash: str,
    ):
        """
        Update or create daily aggregated statistics.
        
        This is called after logging a version check to update the aggregates.
        """
        today = date.today()
        
        # Try to find existing stats for this addon/version/date
        query = select(AddonUsageStats).where(
            AddonUsageStats.addon_id == addon_id,
            AddonUsageStats.date == today,
        )
        if version_id:
            query = query.where(AddonUsageStats.version_id == version_id)
        else:
            query = query.where(AddonUsageStats.version_id.is_(None))
        
        result = await db.execute(query)
        stats = result.scalar_one_or_none()
        
        if stats:
            stats.check_count += 1
            # Note: unique_users is recalculated via scheduled task for accuracy
        else:
            stats = AddonUsageStats(
                addon_id=addon_id,
                version_id=version_id,
                date=today,
                check_count=1,
                unique_users=1,  # Will be recalculated
            )
            db.add(stats)
        
        await db.commit()
    
    @staticmethod
    async def get_addon_analytics(
        db: AsyncSession,
        addon_id: int,
        days: int = 30,
    ) -> AddonAnalyticsResponse:
        """
        Get analytics for a specific addon.
        
        Args:
            addon_id: The addon to get analytics for
            days: Number of days of history (30 for Pro, 90 for Premium)
        """
        # Get addon info
        addon_result = await db.execute(
            select(Addon).where(Addon.id == addon_id)
        )
        addon = addon_result.scalar_one_or_none()
        if not addon:
            raise ValueError(f"Addon {addon_id} not found")
        
        start_date = date.today() - timedelta(days=days)
        
        # Get daily stats aggregated across all versions
        daily_query = select(
            AddonUsageStats.date,
            func.sum(AddonUsageStats.check_count).label("check_count"),
            func.sum(AddonUsageStats.unique_users).label("unique_users"),
        ).where(
            AddonUsageStats.addon_id == addon_id,
            AddonUsageStats.date >= start_date,
        ).group_by(AddonUsageStats.date).order_by(AddonUsageStats.date)
        
        daily_result = await db.execute(daily_query)
        daily_rows = daily_result.all()
        
        daily_stats = [
            DailyStats(
                date=row.date,
                check_count=row.check_count or 0,
                unique_users=row.unique_users or 0,
            )
            for row in daily_rows
        ]
        
        # Get version distribution
        version_query = select(
            AddonUsageStats.version_id,
            func.sum(AddonUsageStats.check_count).label("check_count"),
            func.sum(AddonUsageStats.unique_users).label("unique_users"),
        ).where(
            AddonUsageStats.addon_id == addon_id,
            AddonUsageStats.date >= start_date,
            AddonUsageStats.version_id.isnot(None),
        ).group_by(AddonUsageStats.version_id)
        
        version_result = await db.execute(version_query)
        version_rows = version_result.all()
        
        # Get version names
        version_ids = [row.version_id for row in version_rows if row.version_id]
        versions_map = {}
        if version_ids:
            versions_result = await db.execute(
                select(Version).where(Version.id.in_(version_ids))
            )
            for v in versions_result.scalars():
                versions_map[v.id] = v.version
        
        # Calculate totals and percentages
        total_checks = sum(row.check_count or 0 for row in version_rows)
        total_unique = sum(row.unique_users or 0 for row in version_rows)
        
        version_distribution = []
        for row in version_rows:
            if row.version_id:
                percentage = (row.check_count / total_checks * 100) if total_checks > 0 else 0
                version_distribution.append(
                    VersionDistribution(
                        version=versions_map.get(row.version_id, "Unknown"),
                        version_id=row.version_id,
                        check_count=row.check_count or 0,
                        unique_users=row.unique_users or 0,
                        percentage=round(percentage, 2),
                    )
                )
        
        # Sort by check_count descending
        version_distribution.sort(key=lambda x: x.check_count, reverse=True)
        
        return AddonAnalyticsResponse(
            addon_id=addon_id,
            addon_name=addon.name,
            addon_slug=addon.slug,
            period_days=days,
            total_checks=total_checks,
            total_unique_users=total_unique,
            daily_stats=daily_stats,
            version_distribution=version_distribution,
        )
    
    @staticmethod
    async def get_user_analytics_summary(
        db: AsyncSession,
        user_id: int,
        days: int = 30,
    ) -> AnalyticsSummary:
        """
        Get analytics summary for all of a user's addons.
        
        Args:
            user_id: The user whose addons to get analytics for
            days: Number of days of history
        """
        # Get all user's addons
        addons_result = await db.execute(
            select(Addon).where(Addon.owner_id == user_id)
        )
        addons = addons_result.scalars().all()
        
        addon_analytics = []
        total_checks = 0
        total_unique = 0
        
        for addon in addons:
            try:
                analytics = await AnalyticsService.get_addon_analytics(
                    db, addon.id, days
                )
                addon_analytics.append(analytics)
                total_checks += analytics.total_checks
                total_unique += analytics.total_unique_users
            except ValueError:
                continue
        
        return AnalyticsSummary(
            total_addons=len(addons),
            total_checks=total_checks,
            total_unique_users=total_unique,
            addons=addon_analytics,
        )
    
    @staticmethod
    async def cleanup_old_data(
        db: AsyncSession,
        retention_days: int = 90,
    ):
        """
        Clean up old version check logs beyond retention period.
        
        This should be run as a scheduled task.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Delete old version checks (raw logs)
        from sqlalchemy import delete
        await db.execute(
            delete(VersionCheck).where(VersionCheck.timestamp < cutoff_date)
        )
        
        # Delete old aggregated stats
        await db.execute(
            delete(AddonUsageStats).where(
                AddonUsageStats.date < cutoff_date.date()
            )
        )
        
        await db.commit()
    
    @staticmethod
    async def recalculate_unique_users(
        db: AsyncSession,
        target_date: Optional[date] = None,
    ):
        """
        Recalculate unique user counts from version check logs.
        
        This should be run as a scheduled task (e.g., daily).
        """
        target = target_date or date.today()
        start_of_day = datetime.combine(target, datetime.min.time())
        end_of_day = datetime.combine(target, datetime.max.time())
        
        # Get unique IP hashes per addon/version
        unique_query = select(
            VersionCheck.addon_id,
            VersionCheck.version_id,
            func.count(func.distinct(VersionCheck.client_ip_hash)).label("unique_users"),
        ).where(
            VersionCheck.timestamp >= start_of_day,
            VersionCheck.timestamp <= end_of_day,
        ).group_by(VersionCheck.addon_id, VersionCheck.version_id)
        
        result = await db.execute(unique_query)
        
        for row in result.all():
            # Update the corresponding stats record
            stats_query = select(AddonUsageStats).where(
                AddonUsageStats.addon_id == row.addon_id,
                AddonUsageStats.date == target,
            )
            if row.version_id:
                stats_query = stats_query.where(
                    AddonUsageStats.version_id == row.version_id
                )
            else:
                stats_query = stats_query.where(
                    AddonUsageStats.version_id.is_(None)
                )
            
            stats_result = await db.execute(stats_query)
            stats = stats_result.scalar_one_or_none()
            
            if stats:
                stats.unique_users = row.unique_users
        
        await db.commit()
