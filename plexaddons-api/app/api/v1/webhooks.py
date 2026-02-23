"""Webhook endpoint management API routes (Premium feature)."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.api.deps import get_current_user, get_effective_tier, rate_limit_check_authenticated
from app.models import User, SubscriptionTier, WebhookEndpoint, WebhookDelivery
from app.schemas import (
    WebhookEndpointCreate, WebhookEndpointUpdate, WebhookEndpointResponse,
    WebhookDeliveryResponse, WebhookTestResponse
)
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

MAX_ENDPOINTS = 10


def _require_premium(user: User):
    effective_tier = get_effective_tier(user)
    if effective_tier != SubscriptionTier.PREMIUM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook endpoints require Premium subscription"
        )


def _mask_secret(secret: str) -> str:
    return f"whsec_{secret[:4]}...{secret[-4:]}"


@router.get("/endpoints", response_model=list[WebhookEndpointResponse])
async def list_webhook_endpoints(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List all webhook endpoints for the current user."""
    _require_premium(user)

    result = await db.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.user_id == user.id)
        .order_by(WebhookEndpoint.created_at)
    )
    endpoints = result.scalars().all()

    return [
        WebhookEndpointResponse(
            id=ep.id, name=ep.name, url=ep.url, is_active=ep.is_active,
            event_filter=ep.event_filter, payload_template=ep.payload_template,
            has_secret=True, masked_secret=_mask_secret(ep.secret),
            created_at=ep.created_at, updated_at=ep.updated_at,
        )
        for ep in endpoints
    ]


@router.post("/endpoints", response_model=WebhookEndpointResponse, status_code=201)
async def create_webhook_endpoint(
    data: WebhookEndpointCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Create a new webhook endpoint. Max 10 per user."""
    _require_premium(user)

    count_result = await db.execute(
        select(func.count()).where(WebhookEndpoint.user_id == user.id)
    )
    count = count_result.scalar() or 0
    if count >= MAX_ENDPOINTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_ENDPOINTS} webhook endpoints allowed"
        )

    secret = WebhookService.generate_webhook_secret()
    endpoint = WebhookEndpoint(
        user_id=user.id,
        name=data.name,
        url=data.url,
        secret=secret,
        is_active=data.is_active,
        event_filter=data.event_filter,
        payload_template=data.payload_template,
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)

    return WebhookEndpointResponse(
        id=endpoint.id, name=endpoint.name, url=endpoint.url,
        is_active=endpoint.is_active, event_filter=endpoint.event_filter,
        payload_template=endpoint.payload_template,
        has_secret=True, masked_secret=_mask_secret(endpoint.secret),
        created_at=endpoint.created_at, updated_at=endpoint.updated_at,
    )


@router.patch("/endpoints/{endpoint_id}", response_model=WebhookEndpointResponse)
async def update_webhook_endpoint(
    endpoint_id: int,
    data: WebhookEndpointUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Update a webhook endpoint."""
    _require_premium(user)

    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.user_id == user.id,
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(endpoint, key, value)

    await db.commit()
    await db.refresh(endpoint)

    return WebhookEndpointResponse(
        id=endpoint.id, name=endpoint.name, url=endpoint.url,
        is_active=endpoint.is_active, event_filter=endpoint.event_filter,
        payload_template=endpoint.payload_template,
        has_secret=True, masked_secret=_mask_secret(endpoint.secret),
        created_at=endpoint.created_at, updated_at=endpoint.updated_at,
    )


@router.delete("/endpoints/{endpoint_id}", status_code=204)
async def delete_webhook_endpoint(
    endpoint_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Delete a webhook endpoint and all its delivery history."""
    _require_premium(user)

    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.user_id == user.id,
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    await db.delete(endpoint)
    await db.commit()


@router.post("/endpoints/{endpoint_id}/rotate-secret", response_model=dict)
async def rotate_endpoint_secret(
    endpoint_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Rotate the signing secret for an endpoint. Full secret shown only once."""
    _require_premium(user)

    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.user_id == user.id,
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    new_secret = WebhookService.generate_webhook_secret()
    endpoint.secret = new_secret
    await db.commit()

    return {"secret": new_secret}


@router.post("/endpoints/{endpoint_id}/test", response_model=WebhookTestResponse)
async def test_webhook_endpoint(
    endpoint_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Send a test event to a specific endpoint."""
    _require_premium(user)

    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.user_id == user.id,
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    test_result = await WebhookService.test_endpoint(endpoint)
    return WebhookTestResponse(**test_result)


# ============== Delivery Log ==============

@router.get("/endpoints/{endpoint_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_deliveries(
    endpoint_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """List delivery history for an endpoint (last 100 kept)."""
    _require_premium(user)

    # Verify endpoint ownership
    ep_result = await db.execute(
        select(WebhookEndpoint.id).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.user_id == user.id,
        )
    )
    if not ep_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    query = (
        select(WebhookDelivery)
        .where(WebhookDelivery.endpoint_id == endpoint_id)
    )
    if status_filter:
        query = query.where(WebhookDelivery.status == status_filter)

    query = query.order_by(desc(WebhookDelivery.created_at))
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    deliveries = result.scalars().all()

    return [
        WebhookDeliveryResponse(
            id=d.id, endpoint_id=d.endpoint_id, event_type=d.event_type,
            status=d.status, status_code=d.status_code,
            error_message=d.error_message, attempt=d.attempt,
            max_attempts=d.max_attempts, next_retry_at=d.next_retry_at,
            created_at=d.created_at, delivered_at=d.delivered_at,
        )
        for d in deliveries
    ]


@router.post("/endpoints/{endpoint_id}/deliveries/{delivery_id}/retry", response_model=WebhookDeliveryResponse)
async def retry_delivery(
    endpoint_id: int,
    delivery_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check_authenticated),
):
    """Manually retry a failed delivery."""
    _require_premium(user)

    # Verify endpoint ownership
    ep_result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.user_id == user.id,
        )
    )
    endpoint = ep_result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    result = await db.execute(
        select(WebhookDelivery).where(
            WebhookDelivery.id == delivery_id,
            WebhookDelivery.endpoint_id == endpoint_id,
        )
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    if delivery.status == "success":
        raise HTTPException(status_code=400, detail="Cannot retry a successful delivery")

    # Attempt redelivery
    success, status_code, error = await WebhookService.deliver_to_endpoint(
        endpoint, delivery.event_type, delivery.payload
    )

    delivery.attempt += 1
    delivery.status_code = status_code
    if success:
        from datetime import datetime, timezone
        delivery.status = "success"
        delivery.delivered_at = datetime.now(timezone.utc)
        delivery.error_message = None
        delivery.next_retry_at = None
    else:
        delivery.status = "failed"
        delivery.error_message = error

    await db.commit()
    await db.refresh(delivery)

    return WebhookDeliveryResponse(
        id=delivery.id, endpoint_id=delivery.endpoint_id,
        event_type=delivery.event_type, status=delivery.status,
        status_code=delivery.status_code, error_message=delivery.error_message,
        attempt=delivery.attempt, max_attempts=delivery.max_attempts,
        next_retry_at=delivery.next_retry_at,
        created_at=delivery.created_at, delivered_at=delivery.delivered_at,
    )
