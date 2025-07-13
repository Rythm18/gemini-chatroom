from fastapi import APIRouter
from app.api.v1.endpoints import auth, user, chatroom, webhook
from app.api.v1.endpoints.subscription import subscribe_router, subscription_router

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(user.router, prefix="/user", tags=["user"])
router.include_router(chatroom.router, prefix="/chatroom", tags=["chatroom"])
router.include_router(subscribe_router, prefix="/subscribe", tags=["subscription"])
router.include_router(subscription_router, prefix="/subscription", tags=["subscription"])
router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
