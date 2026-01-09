from fastapi import APIRouter
from app.api.v1 import auth, users, addons, versions, payments, admin, tickets, profiles, analytics, tags, organizations, automation

router = APIRouter(prefix="/v1")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(profiles.router)
router.include_router(addons.router)
router.include_router(versions.router)
router.include_router(analytics.router)
router.include_router(payments.router)
router.include_router(admin.router)
router.include_router(tickets.router)
router.include_router(tags.router)
router.include_router(organizations.router)
router.include_router(automation.router)
