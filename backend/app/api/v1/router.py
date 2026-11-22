from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    chatbot,
    documents,
    eligibility,
    fact_verification,
    grievances,
    media_analysis,
    policy,
    schemes,
    service_automation,
    tracking,
    users,
)

api_router = APIRouter()
for module in (
    auth,
    users,
    schemes,
    documents,
    chatbot,
    eligibility,
    grievances,
    tracking,
    service_automation,
    fact_verification,
    media_analysis,
    policy,
    admin,
):
    api_router.include_router(module.router)
