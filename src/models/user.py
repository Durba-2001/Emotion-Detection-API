# Import BaseModel and Field from Pydantic for data validation 
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal
# Model for creating a new user
class UserCreate(BaseModel):
    # Username field with validation: required, minimum 3 chars, maximum 50 chars
    username: str = Field(..., min_length=3, max_length=50)
    # Password field with validation: required, minimum 6 chars
    password: str = Field(..., min_length=6)
    role: Literal["admin", "user"] = Field(..., description="Role of the user (admin or user)")

# Model for user login
class UserLogin(BaseModel):
    # Username field (required)
    username: str
    # Password field (required)
    password: str
class UserResponse(BaseModel):
    user_id:str
    username:str
    role:str
    created_at: datetime