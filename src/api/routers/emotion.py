from fastapi import APIRouter, Depends, UploadFile, File, Query, Path,Body  # Import FastAPI router, dependency injection, file upload, query/path parameters
from typing import List, Optional,Union # For typing hints (list of files, optional query params)
from src.api.dependencies.auth import get_current_user  # Dependency to get the logged-in user from JWT token
from src.services.emotion_service import analyzed_emotion_from_image  # Service to analyze emotions from an image
from src.models.emotion import EmotionCreate, EmotionResponse  # Pydantic models for request and response validation
from src.schemas.emotion import EmotionSchema  # MongoDB document schema for emotions
from src.api.dependencies.database import get_db  # Dependency to get MongoDB database
from src.utils.errors import validation_error,not_found,forbid_error  # Custom error for validation failures
from src.services.image_service import validate_image  # Service to validate image size & format
from datetime import datetime, timezone
from bson import ObjectId
from src.utils.logger import logger
from src.utils.constants import EMOJI_MAP,CATEGORIES
# Create a router for all emotion-related endpoints
router = APIRouter(tags=["Emotions"])

# Endpoint: Upload and analyze one or multiple images
@router.post("", response_model=List[EmotionResponse], status_code=201)
async def upload_and_analyze_images(
    files: Optional[List[UploadFile]] = File(None),  # Accept multiple uploaded files
    current_user=Depends(get_current_user),  # Get current logged-in user
    db=Depends(get_db)  # Get database connection
):
    
    if not files or len(files) == 0:    # Check if no files were uploaded
        logger.error("No files uploaded")
        not_found("No files uploaded")  
    logger.info(f"User {current_user.username} uploading {len(files)} files")
    results = []  # Prepare list to store results for all images
    for file in files:  # Loop through each uploaded file
        logger.info(f"Validating file: {file.filename}")
        await validate_image(file)  # Validate image format and size
        logger.info(f"Analyzing emotion for file: {file.filename}")
        emotion_data = await analyzed_emotion_from_image(file)  # Analyze emotion using LLM
        
        # Prepare a MongoDB document using EmotionSchema
        emotion_doc = EmotionSchema(
            user_id=current_user.user_id,  # Associate with current user
            filename=file.filename,  # Store original filename
            emotion=emotion_data["emotion"],  # Detected emotion
            emoji=emotion_data["emoji"],  # Corresponding emoji
            metadata=emotion_data.get("metadata", {}) , # Optional metadata (like image size)
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        insert_result = await db.emotions.insert_one(emotion_doc.model_dump())  # Insert document into MongoDB
        emotion_id = str(insert_result.inserted_id)
        logger.info(f"Inserted emotion record: {emotion_id} for file: {file.filename}")

        # Prepare API response using EmotionResponse model
        results.append(EmotionResponse(
            id=emotion_id,  
            user_id=emotion_doc.user_id,
            filename=emotion_doc.filename,
            emotion=emotion_doc.emotion,
            emoji=emotion_doc.emoji,
            created_at=emotion_doc.created_at,
            updated_at=emotion_doc.updated_at,
            metadata=emotion_doc.metadata
        ))
    logger.success(f"Successfully processed {len(results)} file(s) for user: {current_user.username}")
    return results  # Return the list of emotion analysis results

# Endpoint: Get all emotion records with optional filters
@router.get("", response_model=List[EmotionResponse])
async def get_emotions(
    user_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    # Admin sees all (can filter by user_id), normal user sees only their own
    if current_user.role == "admin" and user_id:
        query = {"user_id": user_id}
    elif current_user.role == "admin":
        query = {}  
    else:
        if user_id and user_id != current_user.user_id:
            raise forbid_error(f"You are not allowed to access other user's records whose id {user_id}")
        query = {"user_id": current_user.user_id}

    records = db.emotions.find(query)
    
    results = []
    async for r in records:
        r["id"] = str(r["_id"])   # map ObjectId to string id
        del r["_id"]              # remove _id to avoid duplication
        results.append(EmotionResponse(**r))

    if not results:
        raise not_found("No emotion records found")
    return results


@router.get("/{id}", response_model=EmotionResponse)
async def get_emotion_record_with_id(
    id: str = Path(..., description="ID of the emotion record"),
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    try:
        object_id = ObjectId(id)
        query = {"_id": object_id}
        logger.info(f"Parsed ID as ObjectId: {object_id}")
    except Exception:
        query = {"custom_id": id}
        logger.info(f"Using custom_id for query: {id}")
    # Apply user_id filter only if not admin
    if current_user.role != "admin":
        query["user_id"] = current_user.user_id
        logger.info(f"User is not admin, applying user filter: {current_user.user_id}")
    record = await db.emotions.find_one(query)

    if not record:
        logger.error(f"No emotion records found with id: {id}")
        raise not_found(f"No emotion records found with id: {id}")

    record["id"] = str(record["_id"])
    del record["_id"]
    logger.success(f"Emotion record retrieved successfully | record_id={record['id']} | user_id={record['user_id']}")
    return EmotionResponse(**record)



# Endpoint: Update an emotion record
@router.put("/{id}", response_model=EmotionResponse)
async def update_emotion_record(
    id: str,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
    emotion: EmotionCreate = Body(...)
):
    logger.info(f"Update request started | record_id={id} | user_id={current_user.user_id} | role={current_user.role}")
    
    # Parse ID
    try:
        object_id = ObjectId(id)
        query = {"_id": object_id}
    except Exception:
        query = {"custom_id": id}

    # Non-admins can only access their own records
    if current_user.role != "admin":
        query["user_id"] = current_user.user_id

    record = await db.emotions.find_one(query)
    if not record:
        raise not_found("Record not found")

    update_data = emotion.model_dump(exclude_unset=True)

    # Restrict normal users
    if current_user.role != "admin":
        if record["user_id"] != current_user.user_id:
            raise validation_error("You are not allowed to update this record")
        if "user_id" in update_data and update_data["user_id"] != current_user.user_id:
            raise forbid_error(f"You are not allowed to update another user's record (user_id={update_data['user_id']})")

        # Only emotion + metadata allowed
        allowed_fields = {}
        if "emotion" in update_data:
            allowed_fields["emotion"] = update_data["emotion"]
        if "metadata" in update_data:
            allowed_fields["metadata"] = {**(record.get("metadata") or {}), **update_data["metadata"]}
        update_data = allowed_fields

    # Auto-set emoji if emotion provided
    if "emotion" in update_data and update_data["emotion"]:
        emotion_val = update_data["emotion"].lower()
        if emotion_val not in CATEGORIES:
            raise validation_error(f"Invalid emotion '{emotion_val}', must be one of {list(CATEGORIES)}")
        update_data["emoji"] = EMOJI_MAP[emotion_val]

    # Always update timestamp
    update_data["updated_at"] = datetime.now(timezone.utc)

    # Update DB
    await db.emotions.update_one({"_id": record["_id"]}, {"$set": update_data})
    updated_record = await db.emotions.find_one({"_id": record["_id"]})

    updated_record["id"] = str(updated_record["_id"])
    del updated_record["_id"]

    logger.success(f"Update successful | record_id={updated_record['id']}")
    return EmotionResponse(**updated_record)

# Endpoint: Delete an emotion record
@router.delete("/{id}", status_code=204)
async def delete_emotion_record(
    id: str,  # ID of record to delete
    current_user=Depends(get_current_user),  # Get logged-in user
    db=Depends(get_db)  # Get database connection
):
    logger.info(f"Delete request for record ID: {id} by user: {current_user.username}")
    record = None

    try:
        object_id = ObjectId(id)
        query = {"_id": object_id}
    except Exception as e:
        logger.warning(f"ID is not a valid ObjectId: {id}, trying custom_id. Error: {e}")
        query = {"custom_id": id}

    # Admin can delete any record, normal users can only delete their own
    if current_user.role != "admin":
        query["user_id"] = current_user.user_id

    record = await db.emotions.find_one(query)

    if not record:
        logger.error(f"Record not found for ID: {id}")
        raise not_found("Record not found")

    # RBAC check: if not admin, must be owner
    if current_user.role != "admin" and record["user_id"] != current_user.user_id:
        logger.error(f"User {current_user.username} not allowed to delete record {id}")
        raise validation_error("You are not allowed to delete this record")

    await db.emotions.delete_one({"_id": record["_id"]})  # Delete record
    logger.success(f"Record successfully deleted: {record['_id']}")
    return {"message": "Deleted successfully"}
