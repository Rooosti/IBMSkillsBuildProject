from pydantic import BaseModel
from typing import List, Optional

class RecommendedGame(BaseModel):
    steam_app_id: int
    title: str
    recommendation_score: float
    short_description: Optional[str] = None
    header_image_url: Optional[str] = None
    store_url: Optional[str] = None
    genres: List[str] = []
    tags: List[str] = []
    playtime_minutes: Optional[int] = None
    is_owned: bool = False

class RecommendationResponse(BaseModel):
    recommendations: List[RecommendedGame]
