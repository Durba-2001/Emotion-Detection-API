from pydantic import BaseModel, Field
from datetime import datetime

class EmotionSchema(BaseModel):
    _id: str 
    user_id: str
    filename: str
    emotion: str
    emoji: str
    created_at: datetime
    updated_at: datetime
    metadata: dict
