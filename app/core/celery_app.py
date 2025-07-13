from celery import Celery
from app.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

celery_app = Celery(
    "gemini_chatroom",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks.message_tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    
    result_expires=3600,  # 1 hour
    
    timezone='UTC',
    enable_utc=True,
    
    worker_pool='prefork' if os.getenv('RENDER') else 'solo',
    worker_concurrency=2 if os.getenv('RENDER') else 1,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
)

logger.info("Celery application configured successfully") 