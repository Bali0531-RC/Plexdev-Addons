from fastapi import APIRouter, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.database import get_db
from app.services import StripeService, PayPalService
from app.api.deps import rate_limit_check

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    result = await StripeService.handle_webhook_event(db, payload, sig_header, background_tasks)
    return result


@router.post("/paypal")
async def paypal_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_check),
):
    """Handle PayPal webhook events."""
    payload = await request.json()
    headers = dict(request.headers)
    
    result = await PayPalService.handle_webhook_event(db, payload, headers, background_tasks)
    return result
