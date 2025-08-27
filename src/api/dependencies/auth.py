import os
from jose import jwt, JWTError               # Import JWT handling functions (encode/decode) and error class
from datetime import datetime, timedelta ,timezone    #  For setting token expiration times
from fastapi import Depends                       # For dependency 
from fastapi.security import OAuth2PasswordBearer  # OAuth2 scheme (Bearer token in Authorization header)
from passlib.context import CryptContext                 # Import CryptContext from passlib for password hashing and verification
from src.api.dependencies.database import get_db                     # Custom function to get MongoDB connection
from dotenv import load_dotenv,find_dotenv      # Load environment variables from .env file
from src.utils.errors import  unauthorized # import error helpers
from src.schemas.user import UserSchema
from src.utils.logger import logger   
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Define OAuth2 authentication scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
load_dotenv(find_dotenv())   
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")   # Get secret key for JWT signing from environment
ALGORITHM = os.environ.get("JWT_ALGORITHM")     # Get algorithm for JWT from environment
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(data: dict, expires_delta: timedelta=None):
                            # Copy the input data so we don’t modify the original
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))    # Set expiration time -> now + default (60 mins) or custom delta
    payload = {
    "sub": data.get("username"),   
    "user_id": data.get("user_id"),
    "role": data.get("role"),
    "exp": expire
}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# Authenticate username + password
async def authenticate_user(db,username: str, password: str):
    user = await db["users"].find_one({"username": username})
    if not user:
        logger.warning(f"Authentication failed: user '{username}' not found in DB")
        raise unauthorized("Could not validate user.")
    
    user_doc = UserSchema(**user)   # Convert dict -> Pydantic schema

    if not pwd_context.verify(password, user_doc.hashed_password):
        logger.warning(f"Authentication failed: user password '{password}' not found in DB")
        raise unauthorized("Incorrect username or password")
    return user_doc

# Extracts and verifies user info from token for protected routes
async def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise unauthorized("Invalid token: missing user_id")

        user = await db["users"].find_one({"user_id": user_id})
        if not user:
            raise unauthorized("Could not validate user.")

        return UserSchema(**user)
    except JWTError:
        raise unauthorized("Invalid token")