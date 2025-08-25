import os
from dotenv import load_dotenv,find_dotenv  
from google import genai
from src.utils.constants import EMOJI_MAP,CATEGORIES
from src.utils.logger import logger
from src.services.image_service import validate_image
import tempfile
try:    
    load_dotenv(find_dotenv())
    api_key = os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
except Exception as e:
    logger.error(f"Failed to connect with the api key.{e}")

async def get_llm_response(prompt, file):
    # reset pointer in case it was read before
    file.file.seek(0)

    # save UploadFile to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

   
    myfile = client.files.upload(file=tmp_path)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, myfile]
    )

    # cleanup
    os.remove(tmp_path)

    return response.text.strip().lower()

async def analyzed_emotion_from_image(file):
    # Validate image
    await validate_image(file)

   
    image_bytes = await file.read()
    
    file_size_bytes = len(image_bytes)
    file.file.seek(0)
    prompt = f"""
You are a highly accurate emotion detection system.
Analyze the uploaded image file of a human face.
From the following list of emotions: {list(EMOJI_MAP.keys())},
identify exactly one dominant emotion.

Return only the emotion keyword: it must be exactly one of the listed words,
in lowercase, with no punctuation, no additional words or explanation.
"""


    # Get LLM response
    emotion = await get_llm_response(prompt,file)

    # Check and map emoji
    if emotion in CATEGORIES:
        emoji = EMOJI_MAP[emotion]
    else:
        logger.warning(f"Unexpected emotion from LLM: {emotion}")
        emotion = "unknown"
        emoji = "❓"

    result = {
        "emotion": emotion,
        "emoji": emoji,
        "metadata": {
            "filename": file.filename,
            "content_type": file.content_type,
            "Image_size": file_size_bytes,

        }
    }

    return result
