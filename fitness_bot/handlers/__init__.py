from aiogram import Router

from .common import router as common_router
from .trainer import router as trainer_router
from .trainee import router as trainee_router

router = Router()
router.include_router(common_router)
router.include_router(trainer_router)
router.include_router(trainee_router)
