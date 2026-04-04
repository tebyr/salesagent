from fastapi import APIRouter
from app.api.v1.admin import auth, dashboard, salespersons, clients, goals, settings, productos

router = APIRouter(prefix="/admin")

router.include_router(auth.router)
router.include_router(dashboard.router)
router.include_router(salespersons.router)
router.include_router(clients.router)
router.include_router(goals.router)
router.include_router(settings.router)
router.include_router(productos.router)
