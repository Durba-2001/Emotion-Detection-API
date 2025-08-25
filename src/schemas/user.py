from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserSchema(BaseModel):
    user_id:str
    username: str
    hashed_password: Optional[str] = None
    role: Optional[str] = None
    created_at: Optional[datetime] = None
