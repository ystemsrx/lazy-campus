from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.moderation import router as moderation_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.tasks import router as task_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.users import router as user_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(task_router)
api_router.include_router(moderation_router)
api_router.include_router(notifications_router)
api_router.include_router(uploads_router)
api_router.include_router(chat_router)
