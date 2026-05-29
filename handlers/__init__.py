"""Routerlarni ulash."""

from aiogram import Router

from handlers.common import router as common_router
from handlers.group import router as group_router
from handlers.hub_test import router as hub_test_router
from handlers.masul import router as masul_router
from handlers.operators_admin import router as operators_admin_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(common_router)
    root.include_router(hub_test_router)
    root.include_router(operators_admin_router)
    root.include_router(masul_router)
    root.include_router(group_router)
    return root
