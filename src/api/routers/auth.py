from fastapi import APIRouter, Depends,Form   # For creating routes and handling HTTP errors
from pydantic import BaseModel                 # Import BaseModel from Pydantic for request validation
from passlib.context import CryptContext       # Import CryptContext from passlib for password hashing and verification
from src.utils.logger import logger                # Import custom logger to log activities
from src.api.dependencies.database import get_db       # Import function to get database connection 
from src.utils.errors import  unauthorized, validation_error # import error helpers
from src.models.user import UserCreate,UserResponse
from src.schemas.user import UserSchema
from src.api.dependencies.auth import create_access_token
from datetime import datetime, timezone
from fastapi.security import OAuth2PasswordRequestForm
from src.api.dependencies.auth import authenticate_user
router = APIRouter()                          # Create a router object to group related endpoints (register, login)

# Password hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# register endpoint
@router.post("/register",response_model=UserResponse)
async def register(user:UserCreate,db=Depends(get_db)):
    logger.info(f"Register endpoint called for: {user.username}")      # Log when register endpoint is called
    #db = await get_db()                                                   # Get database connection (MongoDB instance)
    existing = await db.users.find_one({"username": user.username})    # Check if username already exists in the "users" collection

    # If user already exists, log error and raise HTTP 409 Conflict
    if existing:
        logger.error(f"User already exists: {user.username}")
        raise validation_error("User already exists") 
    # Generate sequential user_id (U_001, U_002...)
    count = await db.users.count_documents({})
    user_id = f"U_{count + 1:03d}"
    hashed_pw = pwd_context.hash(user.password)
    user_doc = UserSchema(user_id=user_id,username=user.username,
        hashed_password=hashed_pw,
        role=user.role,
        created_at=datetime.now(timezone.utc))
       
    await db.users.insert_one(user_doc.model_dump())
    logger.info(f"User registered: {user.username} with user_id {user_id}")

    # Return safe response
    return UserResponse(
        user_id=user_doc.user_id,
        username=user_doc.username,
        role=user_doc.role,
        created_at=user_doc.created_at
    )
# login endpoints
@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(),db=Depends(get_db)):
    #logger.info(f"Login attempt for: {user.username}")     # Log when login attempt is made
    logger.info(f"Login endpoint called for: {form_data.username}") 
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.error(f"Login failed for username: {form_data.username}")   # log failure
        raise unauthorized("Invalid username or password")
    logger.success(f"Login successful for: {user.username}")  # log success
    token = create_access_token({
    "user_id": user.user_id,
    "username": user.username,
    "role": user.role
})

    return {"access_token": token, "token_type": "bearer"}