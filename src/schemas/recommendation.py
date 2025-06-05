from pydantic import BaseModel
from typing import List, Optional

class TagPreferences(BaseModel):
    tags: List[str]

class LocationData(BaseModel):
    latitude: float
    longitude: float
    max_distance_km: Optional[float] = 5.0

class RestaurantRecommendation(BaseModel):
    restaurant_id: int
    restaurant_name: str
    address: str
    category: str

class PostRequest(BaseModel):
    content: str

class TitleResponse(BaseModel):
    title: str
