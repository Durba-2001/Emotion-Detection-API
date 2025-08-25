from loguru import logger  # Import Loguru's logger for easy logging

# Add a log file where all log messages will be stored
logger.add(
    "emotion_api.log",   # Name of the log file
    level="INFO",        # Minimum log level to record (INFO, WARNING, ERROR)
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", # set up time as per my choice then log level after that log message 
    

)