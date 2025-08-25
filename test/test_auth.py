import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo import AsyncMongoClient
from dotenv import load_dotenv,find_dotenv
from src.api.routers import auth
from src.api.dependencies.database import get_db
from src.models.user import UserCreate,UserResponse
from fastapi.security import OAuth2PasswordRequestForm
import os

# ---- Simple DB Setup ----
async def override_get_db():
    load_dotenv(find_dotenv())                # Load environment variables from .env file
    MongoDB_url=os.environ.get("MONGODB_URI")
    client = AsyncMongoClient(MongoDB_url) 
    db = client["test_emotion_db"]
    await db.users.drop()     # clean before each test
    return db


# ---- Test App ----
app = FastAPI()
app.include_router(auth.router, prefix="/auth")
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# ---- Import route functions directly ----
register = auth.register
login = auth.login


# ---- TEST CASES ----
@pytest.mark.asyncio
async def test_register_success():
    db = await override_get_db()
    user_data = UserCreate(username="alice", password="secret123", role= "admin")
    resp = await register(user=user_data, db=db)

    assert resp.username == "alice"
    assert resp.role == "admin"
    assert resp.user_id.startswith("U_")
    


@pytest.mark.asyncio
async def test_register_duplicate_user():
    db = await override_get_db()
    user_data = UserCreate(username="bob", password="secret123", role="user")
    await register(user=user_data, db=db)  # first time ok

    with pytest.raises(Exception):
        await register(user=user_data, db=db)  # should raise validation_error

@pytest.mark.asyncio
async def test_login_success():
    db = await override_get_db()

    # register first
    user_data = UserCreate(username="charlie", password="mypassword", role="user")
    await register(user=user_data, db=db)
    # simulate login form
   
    form = OAuth2PasswordRequestForm(username="charlie", password="mypassword", scope="")

    resp = await login(form_data=form, db=db)
    assert "access_token" in resp
    assert resp["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_user():
    db = await override_get_db()


    form = OAuth2PasswordRequestForm(username="ghost", password="wrongpw", scope="")

    with pytest.raises(Exception):
        await login(form_data=form, db=db)

@pytest.mark.asyncio
async def test_login_wrong_password():
    db = await override_get_db()

    # Register a user
    user_data = UserCreate(username="dave", password="correctpw", role="user")
    await register(user=user_data, db=db)

    # Try logging in with wrong password
    form = OAuth2PasswordRequestForm(username="dave", password="wrongpw", scope="")
    with pytest.raises(Exception):
        await login(form_data=form, db=db)
   
@pytest.mark.asyncio
async def test_login_wrong_username():
    db = await override_get_db()

    # Register real user
    user_data = UserCreate(username="eve", password="testpw", role="user")
    await register(user=user_data, db=db)

    # Try login with wrong username
    form = OAuth2PasswordRequestForm(username="not_eve", password="testpw", scope="")
    with pytest.raises(Exception) :
        await login(form_data=form, db=db)
    
