"""Routerlarni ulash."""

from aiogram import Router

from handlers.common import router as common_router
from handlers.group import router as group_router
from handlers.masul import router as masul_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(common_router)
    root.include_router(masul_router)
    root.include_router(group_router)
    return root
