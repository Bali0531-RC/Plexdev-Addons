from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user
from app.models import (
    User, Addon, StagedRollout, RolloutEvent, RolloutStage, RolloutStatus
)
from app.schemas import (
    StagedRolloutCreate, StagedRolloutUpdate, StagedRolloutResponse,
    StagedRolloutListResponse, RolloutPromoteRequest, RolloutEventResponse,
)

router = APIRouter(prefix="/addons/{addon_id}/rollouts", tags=["rollouts"])

STAGE_ORDER = [
    RolloutStage.CANARY,
    RolloutStage.EARLY,
    RolloutStage.PARTIAL,
    RolloutStage.MAJORITY,
    RolloutStage.FULL,
]

STAGE_PERCENTAGES = {
    RolloutStage.CANARY: 1,
    RolloutStage.EARLY: 5,
    RolloutStage.PARTIAL: 25,
    RolloutStage.MAJORITY: 50,
    RolloutStage.FULL: 100,
}


async def _get_addon_or_404(db: AsyncSession, addon_id: int) -> Addon:
    result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = result.scalar_one_or_none()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    return addon


async def _get_rollout_or_404(db: AsyncSession, rollout_id: int, addon_id: int) -> StagedRollout:
    result = await db.execute(
        select(StagedRollout).where(
            StagedRollout.id == rollout_id,
            StagedRollout.addon_id == addon_id,
        )
    )
    rollout = result.scalar_one_or_none()
    if not rollout:
        raise HTTPException(status_code=404, detail="Rollout not found")
    return rollout


@router.get("", response_model=StagedRolloutListResponse)
async def list_rollouts(
    addon_id: int,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    query = select(StagedRollout).where(StagedRollout.addon_id == addon_id)
    count_query = select(func.count(StagedRollout.id)).where(StagedRollout.addon_id == addon_id)

    if status_filter:
        try:
            rs = RolloutStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status filter")
        query = query.where(StagedRollout.status == rs)
        count_query = count_query.where(StagedRollout.status == rs)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(StagedRollout.created_at.desc()).offset(skip).limit(limit)
    )
    rollouts = list(result.scalars().all())

    # Eagerly load events
    for r in rollouts:
        ev_result = await db.execute(
            select(RolloutEvent).where(RolloutEvent.rollout_id == r.id).order_by(RolloutEvent.created_at)
        )
        r.events = list(ev_result.scalars().all())

    return StagedRolloutListResponse(rollouts=rollouts, total=total)


@router.post("", response_model=StagedRolloutResponse, status_code=201)
async def create_rollout(
    addon_id: int,
    data: StagedRolloutCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check no active rollout for same version
    existing = await db.execute(
        select(StagedRollout).where(
            StagedRollout.addon_id == addon_id,
            StagedRollout.version_id == data.version_id,
            StagedRollout.status.in_([RolloutStatus.DRAFT, RolloutStatus.ACTIVE]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Active rollout already exists for this version")

    rollout = StagedRollout(
        addon_id=addon_id,
        version_id=data.version_id,
        created_by_id=user.id,
        stage=RolloutStage.CANARY,
        percentage=STAGE_PERCENTAGES[RolloutStage.CANARY],
        status=RolloutStatus.DRAFT,
        targeting_rules=data.targeting_rules,
        auto_promote=data.auto_promote,
        auto_promote_after_hours=data.auto_promote_after_hours,
    )
    db.add(rollout)
    await db.flush()

    event = RolloutEvent(
        rollout_id=rollout.id,
        from_stage=None,
        to_stage=RolloutStage.CANARY.value,
        from_percentage=None,
        to_percentage=STAGE_PERCENTAGES[RolloutStage.CANARY],
        triggered_by="manual",
        user_id=user.id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(rollout)
    rollout.events = [event]
    return rollout


@router.get("/{rollout_id}", response_model=StagedRolloutResponse)
async def get_rollout(
    addon_id: int,
    rollout_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    rollout = await _get_rollout_or_404(db, rollout_id, addon_id)
    ev_result = await db.execute(
        select(RolloutEvent).where(RolloutEvent.rollout_id == rollout.id).order_by(RolloutEvent.created_at)
    )
    rollout.events = list(ev_result.scalars().all())
    return rollout


@router.patch("/{rollout_id}", response_model=StagedRolloutResponse)
async def update_rollout(
    addon_id: int,
    rollout_id: int,
    data: StagedRolloutUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    rollout = await _get_rollout_or_404(db, rollout_id, addon_id)
    if rollout.status in (RolloutStatus.COMPLETED, RolloutStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Cannot update a completed or cancelled rollout")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rollout, key, value)

    await db.commit()
    await db.refresh(rollout)
    ev_result = await db.execute(
        select(RolloutEvent).where(RolloutEvent.rollout_id == rollout.id).order_by(RolloutEvent.created_at)
    )
    rollout.events = list(ev_result.scalars().all())
    return rollout


@router.post("/{rollout_id}/activate", response_model=StagedRolloutResponse)
async def activate_rollout(
    addon_id: int,
    rollout_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    rollout = await _get_rollout_or_404(db, rollout_id, addon_id)
    if rollout.status != RolloutStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft rollouts can be activated")

    rollout.status = RolloutStatus.ACTIVE
    await db.commit()
    await db.refresh(rollout)
    ev_result = await db.execute(
        select(RolloutEvent).where(RolloutEvent.rollout_id == rollout.id).order_by(RolloutEvent.created_at)
    )
    rollout.events = list(ev_result.scalars().all())
    return rollout


@router.post("/{rollout_id}/promote", response_model=StagedRolloutResponse)
async def promote_rollout(
    addon_id: int,
    rollout_id: int,
    data: RolloutPromoteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    rollout = await _get_rollout_or_404(db, rollout_id, addon_id)
    if rollout.status != RolloutStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Rollout must be active to promote")
    if rollout.stage == RolloutStage.FULL:
        raise HTTPException(status_code=400, detail="Rollout already at full stage")
    if rollout.stage == RolloutStage.PAUSED:
        raise HTTPException(status_code=400, detail="Unpause rollout before promoting")

    old_stage = rollout.stage
    old_pct = rollout.percentage

    if data.target_stage:
        target = data.target_stage
        if STAGE_ORDER.index(target) <= STAGE_ORDER.index(old_stage):
            raise HTTPException(status_code=400, detail="Target stage must be higher than current stage")
    else:
        idx = STAGE_ORDER.index(old_stage)
        target = STAGE_ORDER[idx + 1]

    from datetime import datetime, timezone
    rollout.stage = target
    rollout.percentage = STAGE_PERCENTAGES[target]
    rollout.promoted_at = datetime.now(timezone.utc)

    if target == RolloutStage.FULL:
        rollout.status = RolloutStatus.COMPLETED

    event = RolloutEvent(
        rollout_id=rollout.id,
        from_stage=old_stage.value,
        to_stage=target.value,
        from_percentage=old_pct,
        to_percentage=STAGE_PERCENTAGES[target],
        triggered_by="manual",
        user_id=user.id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(rollout)

    ev_result = await db.execute(
        select(RolloutEvent).where(RolloutEvent.rollout_id == rollout.id).order_by(RolloutEvent.created_at)
    )
    rollout.events = list(ev_result.scalars().all())
    return rollout


@router.post("/{rollout_id}/pause", response_model=StagedRolloutResponse)
async def pause_rollout(
    addon_id: int,
    rollout_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    rollout = await _get_rollout_or_404(db, rollout_id, addon_id)
    if rollout.status != RolloutStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Only active rollouts can be paused")

    rollout.status = RolloutStatus.PAUSED
    rollout.stage = RolloutStage.PAUSED

    event = RolloutEvent(
        rollout_id=rollout.id,
        from_stage=rollout.stage.value,
        to_stage=RolloutStage.PAUSED.value,
        from_percentage=rollout.percentage,
        to_percentage=rollout.percentage,
        triggered_by="manual",
        user_id=user.id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(rollout)

    ev_result = await db.execute(
        select(RolloutEvent).where(RolloutEvent.rollout_id == rollout.id).order_by(RolloutEvent.created_at)
    )
    rollout.events = list(ev_result.scalars().all())
    return rollout


@router.post("/{rollout_id}/cancel", response_model=StagedRolloutResponse)
async def cancel_rollout(
    addon_id: int,
    rollout_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    rollout = await _get_rollout_or_404(db, rollout_id, addon_id)
    if rollout.status in (RolloutStatus.COMPLETED, RolloutStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Rollout already completed or cancelled")

    old_stage = rollout.stage
    rollout.status = RolloutStatus.CANCELLED

    event = RolloutEvent(
        rollout_id=rollout.id,
        from_stage=old_stage.value,
        to_stage="cancelled",
        from_percentage=rollout.percentage,
        to_percentage=0,
        triggered_by="manual",
        user_id=user.id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(rollout)

    ev_result = await db.execute(
        select(RolloutEvent).where(RolloutEvent.rollout_id == rollout.id).order_by(RolloutEvent.created_at)
    )
    rollout.events = list(ev_result.scalars().all())
    return rollout


@router.post("/{rollout_id}/report-error", status_code=204)
async def report_rollout_error(
    addon_id: int,
    rollout_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint for pavc to report errors during rollout."""
    rollout = await _get_rollout_or_404(db, rollout_id, addon_id)
    if rollout.status == RolloutStatus.ACTIVE:
        rollout.error_reports = (rollout.error_reports or 0) + 1
        await db.commit()


@router.post("/{rollout_id}/check-in", status_code=204)
async def rollout_check_in(
    addon_id: int,
    rollout_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint for pavc to report successful check-in."""
    rollout = await _get_rollout_or_404(db, rollout_id, addon_id)
    if rollout.status == RolloutStatus.ACTIVE:
        rollout.total_checks = (rollout.total_checks or 0) + 1
        await db.commit()
