from fastapi import APIRouter
from app.api.v1.reports import ventas, clientes, metas

router = APIRouter(prefix="/reports")

router.include_router(ventas.router)
router.include_router(clientes.router)
router.include_router(metas.router)
