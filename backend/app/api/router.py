from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.progress import router as progress_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.matches import router as matches_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(users_router)
api_router.include_router(resumes_router)
api_router.include_router(jobs_router)
api_router.include_router(matches_router)
api_router.include_router(interviews_router)
api_router.include_router(progress_router)
api_router.include_router(knowledge_router)
