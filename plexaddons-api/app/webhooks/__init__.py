from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.database import get_db
from app.services import StripeService, PayPalService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    result = await StripeService.handle_webhook_event(db, payload, sig_header)
    return result


@router.post("/paypal")
async def paypal_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle PayPal webhook events."""
    payload = await request.json()
    headers = dict(request.headers)
    
    result = await PayPalService.handle_webhook_event(db, payload, headers)
    return result
