# Import BaseModel and Field from Pydantic for data validation 
from pydantic import BaseModel,Field

from datetime import datetime
from typing import Optional

class Metadata(BaseModel):
    filename: Optional[str]
    content_type: Optional[str]
    Image_size: Optional[int]
# Schema for creating/updating an emotion record
class EmotionCreate(BaseModel):
    user_id: Optional[str] = None
    emotion: str
    metadata: Optional[Metadata]=None
# Schema for storing/retrieving a complete emotion record 
class EmotionResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    emotion: str
    emoji: str
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Metadata]=None  