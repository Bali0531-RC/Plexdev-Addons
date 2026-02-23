from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.api.deps import get_current_user
from app.models import User, Addon, FeatureFlag
from app.schemas import (
    FeatureFlagCreate, FeatureFlagUpdate, FeatureFlagResponse,
    FeatureFlagListResponse, FeatureFlagEvaluateRequest, FeatureFlagEvaluateResponse,
)

router = APIRouter(prefix="/addons/{addon_id}/flags", tags=["feature-flags"])


async def _get_addon_or_404(db: AsyncSession, addon_id: int) -> Addon:
    result = await db.execute(select(Addon).where(Addon.id == addon_id))
    addon = result.scalar_one_or_none()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    return addon


async def _get_flag_or_404(db: AsyncSession, flag_id: int, addon_id: int) -> FeatureFlag:
    result = await db.execute(
        select(FeatureFlag).where(
            FeatureFlag.id == flag_id,
            FeatureFlag.addon_id == addon_id,
        )
    )
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    return flag


@router.get("", response_model=FeatureFlagListResponse)
async def list_flags(
    addon_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    total_result = await db.execute(
        select(func.count(FeatureFlag.id)).where(FeatureFlag.addon_id == addon_id)
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(FeatureFlag)
        .where(FeatureFlag.addon_id == addon_id)
        .order_by(FeatureFlag.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    flags = list(result.scalars().all())
    return FeatureFlagListResponse(flags=flags, total=total)


@router.post("", response_model=FeatureFlagResponse, status_code=201)
async def create_flag(
    addon_id: int,
    data: FeatureFlagCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check for duplicate key
    existing = await db.execute(
        select(FeatureFlag).where(
            FeatureFlag.addon_id == addon_id,
            FeatureFlag.key == data.key,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Flag key already exists for this addon")

    flag = FeatureFlag(
        addon_id=addon_id,
        created_by_id=user.id,
        key=data.key,
        name=data.name,
        description=data.description,
        enabled=data.enabled,
        percentage=data.percentage,
        targeting=data.targeting,
    )
    db.add(flag)
    await db.commit()
    await db.refresh(flag)
    return flag


@router.get("/{flag_id}", response_model=FeatureFlagResponse)
async def get_flag(
    addon_id: int,
    flag_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    return await _get_flag_or_404(db, flag_id, addon_id)


@router.patch("/{flag_id}", response_model=FeatureFlagResponse)
async def update_flag(
    addon_id: int,
    flag_id: int,
    data: FeatureFlagUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    flag = await _get_flag_or_404(db, flag_id, addon_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(flag, key, value)

    await db.commit()
    await db.refresh(flag)
    return flag


@router.delete("/{flag_id}", status_code=204)
async def delete_flag(
    addon_id: int,
    flag_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addon = await _get_addon_or_404(db, addon_id)
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    flag = await _get_flag_or_404(db, flag_id, addon_id)
    await db.delete(flag)
    await db.commit()


@router.post("/evaluate", response_model=list[FeatureFlagEvaluateResponse])
async def evaluate_flags(
    addon_id: int,
    data: FeatureFlagEvaluateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint for pavc to evaluate all flags for an addon."""
    await _get_addon_or_404(db, addon_id)

    result = await db.execute(
        select(FeatureFlag).where(FeatureFlag.addon_id == addon_id)
    )
    flags = list(result.scalars().all())

    evaluated = []
    for flag in flags:
        enabled = flag.enabled
        if enabled and flag.targeting:
            # Check server targeting
            if data.server_id and flag.targeting.get("server_ids"):
                if data.server_id not in flag.targeting["server_ids"]:
                    enabled = False
            # Check user targeting
            if data.user_id and flag.targeting.get("user_ids"):
                if data.user_id not in flag.targeting["user_ids"]:
                    enabled = False

        if enabled and flag.percentage < 100:
            # Deterministic hash-based percentage check
            import hashlib
            hash_input = f"{flag.key}:{data.server_id or ''}:{data.user_id or ''}"
            hash_val = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16) % 100
            enabled = hash_val < flag.percentage

        evaluated.append(FeatureFlagEvaluateResponse(key=flag.key, enabled=enabled))

    return evaluated
