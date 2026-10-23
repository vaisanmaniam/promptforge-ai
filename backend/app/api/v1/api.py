from fastapi import APIRouter
from app.api.v1.endpoints import health, prompts, regression, repair, requirements, system, verification

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(system.router, tags=["System Diagnostics"])
api_router.include_router(prompts.router, prefix="/prompts", tags=["Prompt Intelligence"])
api_router.include_router(requirements.router, prefix="/requirements", tags=["Requirement Intelligence"])
api_router.include_router(verification.router, prefix="/verification", tags=["Code Verification & Sandbox"])
api_router.include_router(regression.router, prefix="/regression", tags=["Predictive Regression Testing"])
api_router.include_router(repair.router, prefix="/repair", tags=["Failure-Guided Code Repair"])

