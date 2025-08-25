# Import BaseModel and Field from Pydantic for data validation 
from pydantic import BaseModel,Field
from bson import ObjectId
from datetime import datetime
from typing import Optional
# Schema for creating/updating an emotion record
class EmotionCreate_forAdmin(BaseModel):
    user_id: Optional[str] = None
    emotion: Optional[str] = None
class EmotionCreate_forUser(BaseModel):
    emotion: str  
# Schema for storing/retrieving a complete emotion record 
class EmotionResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    emotion: str
    emoji: str
    created_at: datetime
    updated_at: datetime
    metadata: dict   