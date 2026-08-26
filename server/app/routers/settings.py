from fastapi import APIRouter

from app import storage
from app.schemas import RubricSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings() -> RubricSettings:
    return storage.load_settings()


@router.put("")
async def update_settings(rubric: RubricSettings) -> RubricSettings:
    storage.save_settings(rubric)
    return rubric
