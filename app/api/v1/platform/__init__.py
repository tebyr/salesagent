from fastapi import APIRouter
from app.api.v1.platform import tenants

router = APIRouter(prefix="/platform")

router.include_router(tenants.router)
