import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from io import BytesIO
from datetime import datetime


from dotenv import load_dotenv, find_dotenv
import os
from pymongo import AsyncMongoClient


from src.api.routers import emotion
from src.api.dependencies import database, auth


# -----------------------

# ---- Simple DB Setup ----
async def override_get_db():
    load_dotenv(find_dotenv())                # Load environment variables from .env file
    MongoDB_url=os.environ.get("MONGODB_URI")
    client = AsyncMongoClient(MongoDB_url) 
    db = client["test_emotion_db"]
    #await db.emotions.drop()     # clean before each test
    return db

# -----------------------
# Fake dependencies
# -----------------------
async def override_user():
    return type("User", (), {"username": "testuser", "role": "user", "user_id": "U123"})

async def override_admin():
    return type("User", (), {"username": "admin", "role": "admin", "user_id": "U999"})


# -----------------------
# Test App
# -----------------------
app = FastAPI()
app.include_router(emotion.router, prefix="/emotions")

# Apply overrides
app.dependency_overrides[database.get_db] = override_get_db
app.dependency_overrides[auth.get_current_user] = override_user
client = TestClient(app)


# -----------------------
# TEST CASES
# -----------------------

@pytest.mark.asyncio
async def test_upload_no_files():
    resp = client.post("/emotions")
    assert resp.status_code == 404
    

@pytest.mark.asyncio
async def test_upload_valid_jpeg_file():
    image_path = "images/happy.jpg"   
    with open(image_path, "rb") as f:
        files = [("files", ("happy.jpg", f, "image/jpeg"))]

        response = client.post("/emotions", files=files)

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert data[0]["emotion"] == "happy"
    assert data[0]["emoji"] == "😊"
    assert data[0]["user_id"] == "U123"
@pytest.mark.asyncio
async def test_upload_multiple_files():
    files = [
        ("files", ("happy.jpg", open("images/happy.jpg", "rb"), "image/jpeg")),
        ("files", ("sad.jpg", open("images/sad.jpg", "rb"), "image/jpeg")),
    ]
    response = client.post("/emotions", files=files)
    assert response.status_code == 201
    data = response.json()
   
    assert len(data) == 2
    assert data[0]["emotion"]  # emotion returned for first
    assert data[1]["emotion"]  # emotion returned for second
@pytest.mark.asyncio
async def test_get_emotion_record_by_id():
    image_path = "images/happy.jpg"   
    with open(image_path, "rb") as f:
        files = [("files", ("happy.jpg", f, "image/jpeg"))]
        response = client.post("/emotions", files=files)
  
    assert response.status_code == 201
    data = response.json()
    
    assert len(data) == 1

    # Extract the inserted record ID (should be present now)
    emotion_id = data[0]["id"]

    # Fetch record by ID
    resp = client.get(f"/emotions/{emotion_id}")
    assert resp.status_code == 200

    record = resp.json()
    assert record["id"] == emotion_id
    assert record["emotion"] == "happy"
    assert record["emoji"] == "😊"
    assert record["user_id"] == "U123"


@pytest.mark.asyncio
async def test_get_emotion_record_by_id_admin():
    # Upload an image as user "U123"
    image_path = "images/happy.jpg"
    with open(image_path, "rb") as f:
        files = [("files", ("happy.jpg", f, "image/jpeg"))]
        response = client.post("/emotions", files=files)
    assert response.status_code == 201
    data = response.json()
    emotion_id = data[0]["id"]

    # Override current_user to admin
    app.dependency_overrides[auth.get_current_user] = override_admin

    # Admin fetches any record 
    resp = client.get(f"/emotions/{emotion_id}")
    assert resp.status_code == 200
    record = resp.json()
    assert record["id"] == emotion_id

    # Reset dependency override back to user
    app.dependency_overrides[auth.get_current_user] = override_user

@pytest.mark.asyncio
async def test_get_all_emotions_user():
    # Upload an image as user "U123"
    image_path = "images/happy.jpg"
    with open(image_path, "rb") as f:
        files = [("files", ("happy.jpg", f, "image/jpeg"))]
        response = client.post("/emotions", files=files)
    assert response.status_code == 201

    # Get all emotions as the same user
    resp = client.get("/emotions")
    assert resp.status_code == 200

    data = resp.json()
   
    assert len(data) >= 1
    for record in data:
        assert record["user_id"] == "U123"  # Ensure user can only see their records


@pytest.mark.asyncio
async def test_get_all_emotions_admin():
    # Upload an image as user "U123"
    image_path = "images/happy.jpg"
    with open(image_path, "rb") as f:
        files = [("files", ("happy.jpg", f, "image/jpeg"))]
        response = client.post("/emotions", files=files)
    assert response.status_code == 201

    # Change to admin user
    app.dependency_overrides[auth.get_current_user] = override_admin

    # Admin gets all emotion records
    resp = client.get("/emotions")
    assert resp.status_code == 200

    data = resp.json()
    
    assert len(data) >= 1
    # Admin should see records of any user, so we do not check user_id here

    # Switch back to normal user if needed
    app.dependency_overrides[auth.get_current_user] = override_user



@pytest.mark.asyncio
async def test_update_emotion_record():
    # Upload an initial image as user "U123"
    image_path = "images/happy.jpg"
    with open(image_path, "rb") as f:
        files = [("files", ("happy.jpg", f, "image/jpeg"))]
        response = client.post("/emotions", files=files)
    assert response.status_code == 201
    data = response.json()
    emotion_id = data[0]["id"]

    # Prepare updated payload (as user)
    payload = {
        "emotion": "sad"  # update to different emotion
    }

    # Send PUT request to update the record
    update_resp = client.put(f"/emotions/{emotion_id}", json=payload)
    assert update_resp.status_code == 200

    updated_record = update_resp.json()
    assert updated_record["id"] == emotion_id
    assert updated_record["emotion"] == "sad"
    # emoji should be updated correspondingly (assuming your logic sets it)
    assert "emoji" in updated_record  

@pytest.mark.asyncio
async def test_normal_user_cannot_update_other_users_record():
    # Upload an initial image as user "U123"
    image_path = "images/sad.jpg"
    with open(image_path, "rb") as f:
        files = [("files", ("sad.jpg", f, "image/jpeg"))]
        response = client.post("/emotions", files=files)
    assert response.status_code == 201
    data = response.json()
    emotion_id = data[0]["id"]

    # Try to update with a different user_id (simulating forbidden attempt)
    payload = {
        "user_id": "some_other_user",   # different from creator
        "emotion": "angry"
    }

    update_resp = client.put(f"/emotions/{emotion_id}", json=payload)

    # Assert forbidden
    assert update_resp.status_code == 403

@pytest.mark.asyncio
async def test_admin_update_emotion_and_user_id():
    # Upload an image as normal user "U123"
    image_path = "images/happy.jpg"
    with open(image_path, "rb") as f:
        files = [("files", ("happy.jpg", f, "image/jpeg"))]
        response = client.post("/emotions", files=files)
    assert response.status_code == 201
    data = response.json()
    emotion_id = data[0]["id"]

    # New payload admin wants to update, including user_id change
    payload = {
        "emotion": "surprised",
        "user_id": "U999"  # Admin changes owner to user U999
    }

    # Override current user to admin
    app.dependency_overrides[auth.get_current_user] = override_admin

    # Send PUT request as admin to update
    update_resp = client.put(f"/emotions/{emotion_id}", json=payload)
    assert update_resp.status_code == 200

    updated_record = update_resp.json()
    assert updated_record["id"] == emotion_id
    assert updated_record["emotion"] == "surprised"
    assert updated_record["user_id"] == "U999"  # Confirm user_id changed

    # Reset dependency override back to normal user
    app.dependency_overrides[auth.get_current_user] = override_user

@pytest.mark.asyncio
async def test_update_with_invalid_emotion(tmp_path):
    # Step 1: Upload an image as admin (or normal user)
    image_path = "images/happy.jpg"
    with open(image_path, "rb") as f:
        files = [("files", ("happy.jpg", f, "image/jpeg"))]
        app.dependency_overrides[auth.get_current_user] = override_admin
        response = client.post("/emotions", files=files)
    assert response.status_code == 201
    emotion_id = response.json()[0]["id"]

    # Step 2: Try updating with invalid emotion
    invalid_payload = {
        "emotion": "angrrryyyy",   # <-- not in CATEGORIES
        "user_id": "U123"
    }
    update_resp = client.put(f"/emotions/{emotion_id}", json=invalid_payload)

    # Step 3: Validate response
    assert update_resp.status_code == 422 or update_resp.status_code == 400
import pytest

@pytest.mark.asyncio
async def test_update_emotion_record_invalid_id():
    # Upload an initial image to create a record
    image_path = "images/happy.jpg"
    with open(image_path, "rb") as f:
        files = [("files", ("happy.jpg", f, "image/jpeg"))]
        response = client.post("/emotions", files=files)
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    created_id = data[0]["id"]   # valid record id

    # Use a fake id instead of created_id
    fake_id = "64a9f1b77c99999999999999"

    # Prepare payload
    payload = {"emotion": "happy"}

    # Try updating with fake id
    update_resp = client.put(f"/emotions/{fake_id}", json=payload)

    # Assert 404 not found
    assert update_resp.status_code == 404
    
@pytest.mark.asyncio
async def test_delete_emotion_record_by_user():
    # Upload an image as user "U123"
    image_path = "images/happy.jpg"
    with open(image_path, "rb") as f:
        files = [("files", ("happy.jpg", f, "image/jpeg"))]
        response = client.post("/emotions", files=files)
    assert response.status_code == 201
    data = response.json()
    emotion_id = data[0]["id"]

    # User deletes their own record - should succeed
    delete_resp = client.delete(f"/emotions/{emotion_id}")
    assert  delete_resp.status_code == 204

@pytest.mark.asyncio
async def test_delete_emotion_record_by_admin():
    app.dependency_overrides[auth.get_current_user] = override_admin
    image_path = "images/sad.jpg"
    with open(image_path, "rb") as f:
        files = [("files", ("sad.jpg", f, "image/jpeg"))]
        response = client.post("/emotions", files=files)
    assert response.status_code == 201
    data = response.json()
    emotion_id = data[0]["id"]

    # Override current_user to admin
   

    # Admin deletes any record - should succeed regardless of user_id
    delete_resp = client.delete(f"/emotions/{emotion_id}")
    assert  delete_resp.status_code == 204

