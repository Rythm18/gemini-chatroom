from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user
from app.models.user import User, SubscriptionTier
from pydantic import BaseModel
import stripe
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)

# Debug print statements
print(f"STRIPE_TEST_SECRET_KEY: {settings.STRIPE_TEST_SECRET_KEY}")
print(f"STRIPE_TEST_PRICE_ID_PRO: {settings.STRIPE_TEST_PRICE_ID_PRO}")
print(f"Stripe API key set: {bool(settings.STRIPE_TEST_SECRET_KEY)}")

stripe.api_key = settings.STRIPE_TEST_SECRET_KEY

class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str

class SubscriptionStatusResponse(BaseModel):
    user_id: int
    subscription_tier: str
    is_pro: bool

subscribe_router = APIRouter()
subscription_router = APIRouter()

@subscribe_router.post("/pro", response_model=CheckoutResponse)
async def subscribe_pro(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ○ Subscription start API
    
    Creates a Stripe checkout session for Pro subscription.
    User visits the returned checkout URL to complete payment.
    """
    try:
        if current_user.subscription_tier == SubscriptionTier.PRO:
            raise HTTPException(
                status_code=400,
                detail="User already has Pro subscription"
            )
        
        # Debug print statements before creating checkout session
        print(f"current_user: {settings.STRIPE_TEST_SECRET_KEY}")
        db.refresh(current_user)
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': settings.STRIPE_TEST_PRICE_ID_PRO,
                'quantity': 1,
            }],
            mode='subscription',
            success_url="https://yourapp.com/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://yourapp.com/cancel",
            client_reference_id=str(current_user.id),
            metadata={
                'user_id': str(current_user.id),
                'mobile_number': current_user.mobile_number
            }
        )
        
        
        return CheckoutResponse(
            checkout_url=checkout_session.url,
            session_id=checkout_session.id
        )
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Stripe error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@subscription_router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ○ Subscription status API for user
    
    Returns the user's current subscription tier and status.
    """
    try:
        return SubscriptionStatusResponse(
            user_id=current_user.id,
            subscription_tier=current_user.subscription_tier.value,
            is_pro=(current_user.subscription_tier == SubscriptionTier.PRO)
        )
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

router = subscription_router 