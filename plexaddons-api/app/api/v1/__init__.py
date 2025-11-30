from fastapi import APIRouter
from app.api.v1 import auth, users, addons, versions, payments, admin, tickets

router = APIRouter(prefix="/v1")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(addons.router)
router.include_router(versions.router)
router.include_router(payments.router)
router.include_router(admin.router)
router.include_router(tickets.router)
