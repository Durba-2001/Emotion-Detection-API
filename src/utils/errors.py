from fastapi import HTTPException, status   # Import FastAPI's built-in HTTPException class and standard HTTP status codes
from src.utils.logger import logger             # Import your custom logger to log errors

# A helper function to raise HTTP exceptions
def api_exception(detail: str, status_code: int):
    logger.error(f"{detail}")               # Log the error message for debugging/monitoring
    raise HTTPException(                    # Raise a FastAPI HTTPException
        status_code=status_code,            # Pass the HTTP status code (e.g., 404, 401, 422)
        detail={"message": detail}          # Response body with only the error message (no extra code field)
    )

# function for "Not Found" (404) errors
def not_found(detail: str = "Resource not found"):
    return api_exception(detail, status.HTTP_404_NOT_FOUND)   # Calls api_exception with status 404

# function for "Unauthorized" (401) errors
def unauthorized(detail: str = "Unauthorized"):
    return api_exception(detail, status.HTTP_401_UNAUTHORIZED)  # Calls api_exception with status 401

#  function for "Validation Error" (422) errors
def validation_error(detail: str = "Validation failed"):
    return api_exception(detail, status.HTTP_422_UNPROCESSABLE_ENTITY)  # Calls api_exception with status 422

def forbid_error(detail:str="Forbidden"):
    return api_exception(detail, status.HTTP_403_FORBIDDEN)
