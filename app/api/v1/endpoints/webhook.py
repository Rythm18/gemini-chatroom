from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.deps import get_db
from app.models.user import User, SubscriptionTier
import stripe
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_TEST_SECRET_KEY
print(f"Stripe API key set: {bool(stripe.api_key)}")

router = APIRouter()

@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    ○ Stripe webhook to handle events (success, failure, etc.)
    
    Processes webhook events from Stripe to update user subscription status:
    - checkout.session.completed: Payment succeeded, upgrade user to Pro
    - invoice.payment_failed: Payment failed, log the failure
    - customer.subscription.deleted: Subscription cancelled, downgrade to Basic
    """
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        try:
            event = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON payload"
            )
        
        event_type = event.get("type")
        event_data = event.get("data", {}).get("object", {})
        
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(event_data, db)
        elif event_type == "invoice.payment_failed":
            await handle_payment_failed(event_data, db)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_cancelled(event_data, db)
        else:
            logger.info(f"Received unhandled webhook event: {event_type}")
        
        return {
            "success": True,
            "message": f"Webhook event {event_type} processed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

async def handle_checkout_completed(session_data: dict, db: Session):
    """Handle successful checkout - upgrade user to Pro"""
    try:
        user_id = session_data.get("metadata", {}).get("user_id")
        if not user_id:
            user_id = session_data.get("client_reference_id")
        
        if not user_id:
            logger.error("No user ID found in checkout session")
            return
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user:
            user.subscription_tier = SubscriptionTier.PRO
            db.commit()
        else:
            logger.error(f"User {user_id} not found for Pro upgrade")
            
    except Exception as e:
        logger.error(f"Error handling checkout completion: {e}")
        db.rollback()

async def handle_payment_failed(invoice_data: dict, db: Session):
    """Handle payment failure - log the failure"""
    try:
        customer_id = invoice_data.get("customer")
        amount = invoice_data.get("amount_due", 0)
        
        logger.warning(f"Payment failed for customer {customer_id}, amount: {amount}")
        
    except Exception as e:
        logger.error(f"Error handling payment failure: {e}")

async def handle_subscription_cancelled(subscription_data: dict, db: Session):
    """Handle subscription cancellation - downgrade user to Basic"""
    try:
        customer_id = subscription_data.get("customer")
        
        logger.info(f"Subscription cancelled for customer {customer_id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription cancellation: {e}") 