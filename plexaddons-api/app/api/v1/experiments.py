"""A/B Testing endpoints (PREM-2)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from app.database import get_db
from app.api.deps import get_current_user, rate_limit_check_authenticated, get_effective_tier
from app.models import (
    User, Addon, ABExperiment, ABVariant, ExperimentStatus, SubscriptionTier,
)
from app.schemas import (
    ABExperimentCreate, ABExperimentUpdate, ABExperimentResponse,
    ABExperimentListResponse,
)

router = APIRouter(
    prefix="/addons/{addon_id}/experiments",
    tags=["A/B Testing"],
)


async def _verify_premium_owner(addon_id: int, user: User, db: AsyncSession) -> Addon:
    """Verify user is Premium and owns the addon."""
    addon = (await db.execute(select(Addon).where(Addon.id == addon_id))).scalar_one_or_none()
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    if addon.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not the addon owner")
    effective_tier = get_effective_tier(user)
    if effective_tier != SubscriptionTier.PREMIUM and not user.is_admin:
        raise HTTPException(status_code=403, detail="A/B testing requires Premium subscription")
    return addon


@router.get("", response_model=ABExperimentListResponse)
async def list_experiments(
    addon_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List all A/B experiments for an addon."""
    await _verify_premium_owner(addon_id, user, db)

    result = await db.execute(
        select(ABExperiment)
        .where(ABExperiment.addon_id == addon_id)
        .order_by(ABExperiment.created_at.desc())
    )
    experiments = result.scalars().all()

    # Eagerly load variants
    for exp in experiments:
        await db.refresh(exp, ["variants"])

    return ABExperimentListResponse(
        experiments=[ABExperimentResponse.model_validate(e) for e in experiments],
        total=len(experiments),
    )


@router.post("", response_model=ABExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    addon_id: int,
    body: ABExperimentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Create a new A/B experiment."""
    await _verify_premium_owner(addon_id, user, db)

    # Validate variant percentages sum to 100
    total_pct = sum(v.percentage for v in body.variants)
    if total_pct != 100:
        raise HTTPException(
            status_code=400,
            detail=f"Variant percentages must sum to 100 (got {total_pct})",
        )

    # Ensure exactly one control
    controls = [v for v in body.variants if v.is_control]
    if len(controls) != 1:
        raise HTTPException(status_code=400, detail="Exactly one variant must be marked as control")

    experiment = ABExperiment(
        addon_id=addon_id,
        created_by_id=user.id,
        name=body.name,
        description=body.description,
        targeting_rules=body.targeting_rules,
        auto_promote=body.auto_promote,
        auto_promote_after_hours=body.auto_promote_after_hours,
    )
    db.add(experiment)
    await db.flush()

    for v in body.variants:
        variant = ABVariant(
            experiment_id=experiment.id,
            version_id=v.version_id,
            name=v.name,
            percentage=v.percentage,
            is_control=v.is_control,
        )
        db.add(variant)

    await db.commit()
    await db.refresh(experiment, ["variants"])
    return ABExperimentResponse.model_validate(experiment)


@router.get("/{experiment_id}", response_model=ABExperimentResponse)
async def get_experiment(
    addon_id: int,
    experiment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Get a specific experiment with its variants."""
    await _verify_premium_owner(addon_id, user, db)

    result = await db.execute(
        select(ABExperiment).where(
            ABExperiment.id == experiment_id,
            ABExperiment.addon_id == addon_id,
        )
    )
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    await db.refresh(experiment, ["variants"])
    return ABExperimentResponse.model_validate(experiment)


@router.patch("/{experiment_id}", response_model=ABExperimentResponse)
async def update_experiment(
    addon_id: int,
    experiment_id: int,
    body: ABExperimentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update an experiment (only allowed in DRAFT status)."""
    await _verify_premium_owner(addon_id, user, db)

    result = await db.execute(
        select(ABExperiment).where(
            ABExperiment.id == experiment_id,
            ABExperiment.addon_id == addon_id,
        )
    )
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.status != ExperimentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only edit experiments in DRAFT status")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(experiment, key, value)

    await db.commit()
    await db.refresh(experiment, ["variants"])
    return ABExperimentResponse.model_validate(experiment)


@router.post("/{experiment_id}/start", response_model=ABExperimentResponse)
async def start_experiment(
    addon_id: int,
    experiment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Start a draft experiment."""
    await _verify_premium_owner(addon_id, user, db)

    result = await db.execute(
        select(ABExperiment).where(
            ABExperiment.id == experiment_id,
            ABExperiment.addon_id == addon_id,
        )
    )
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.status != ExperimentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Experiment is not in DRAFT status")

    # Check no other running experiment for this addon
    running = await db.execute(
        select(func.count(ABExperiment.id)).where(
            ABExperiment.addon_id == addon_id,
            ABExperiment.status == ExperimentStatus.RUNNING,
        )
    )
    if (running.scalar() or 0) > 0:
        raise HTTPException(status_code=409, detail="Another experiment is already running for this addon")

    experiment.status = ExperimentStatus.RUNNING
    experiment.started_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(experiment, ["variants"])
    return ABExperimentResponse.model_validate(experiment)


@router.post("/{experiment_id}/stop", response_model=ABExperimentResponse)
async def stop_experiment(
    addon_id: int,
    experiment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Stop a running experiment."""
    await _verify_premium_owner(addon_id, user, db)

    result = await db.execute(
        select(ABExperiment).where(
            ABExperiment.id == experiment_id,
            ABExperiment.addon_id == addon_id,
        )
    )
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.status not in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
        raise HTTPException(status_code=400, detail="Experiment is not running or paused")

    experiment.status = ExperimentStatus.COMPLETED
    experiment.ended_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(experiment, ["variants"])
    return ABExperimentResponse.model_validate(experiment)


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(
    addon_id: int,
    experiment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Delete an experiment (only in DRAFT or COMPLETED status)."""
    await _verify_premium_owner(addon_id, user, db)

    result = await db.execute(
        select(ABExperiment).where(
            ABExperiment.id == experiment_id,
            ABExperiment.addon_id == addon_id,
        )
    )
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.status in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
        raise HTTPException(status_code=400, detail="Stop the experiment before deleting")

    await db.delete(experiment)
    await db.commit()
