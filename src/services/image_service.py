from PIL import Image
import io
import os
from dotenv import load_dotenv, find_dotenv
from src.utils.errors import validation_error  # import custom error
load_dotenv(find_dotenv())
maxsize = int(os.environ.get("MAX_IMAGE_SIZE"))
ALLOWED_FORMATS = ["JPEG", "PNG"]
async def validate_image(file):
    # Read bytes from uploaded file
    image_data = await file.read()
     # Reset pointer so file can be reused later
    await file.seek(0)
    # Check size before opening image
    if len(image_data) > maxsize:
        raise validation_error("Image size exceeds 10 MB limit")
  # Check file format
    try:
      img = Image.open(io.BytesIO(image_data)) # Read bytes from uploaded file
      img_format=img.format.upper()
      if img_format not in ALLOWED_FORMATS:
            raise validation_error(f"Invalid image format. Allowed: {ALLOWED_FORMATS}")
    except Exception:
        raise validation_error("Invalid image file")
    return image_data
