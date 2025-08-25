from pymongo import AsyncMongoClient   # Import AsyncMongoClient to connect to MongoDB asynchronously
import os                              # Import os to read environment variables
from dotenv import load_dotenv,find_dotenv # Import functions to load variables from a .env file
from src.utils.logger import logger
client=None
# Define an async function to get a MongoDB database
async def get_db(db_name="emotion_db"):
  global client
  load_dotenv(find_dotenv())                # Load environment variables from .env file
  MongoDB_url=os.environ.get("MONGODB_URI") # Get the MongoDB connection URL from environment variables
  
  try:
      if not client:
        logger.info("Connecting to MongoDB...")   # Log info before connecting
        client = AsyncMongoClient(MongoDB_url)    # Create an asynchronous MongoDB client using the connection URL
        logger.info(f"Connected to database: {db_name}")
      db = client[db_name]                      # Get the database with the specified name     
      return db                   # Return the database object for future used       
  except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")  # Log any errors
        return None
                    
# Function to close DB connection
def close_db():
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed")
        client = None   # Reset client so it can reconnect next time