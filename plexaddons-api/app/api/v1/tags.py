"""Tags endpoints for addon categorization."""

from fastapi import APIRouter
from app.models import AddonTag
from app.schemas import TagListResponse

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("", response_model=TagListResponse)
async def list_tags():
    """
    Get all available addon tags.
    Returns the predefined list of tags for categorizing addons.
    """
    return TagListResponse(tags=list(AddonTag))
