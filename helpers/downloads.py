import os
import shutil
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
DB_NAME = os.getenv('DB_NAME', 'pdf_helper_bot')

client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]

# Constants for file operations
DOWNLOAD_DIR = "downloads"  # Directory to store downloads

def create_user_dir(user_id: int) -> str:
    """Create and return user-specific download directory."""
    user_dir = os.path.join(DOWNLOAD_DIR, str(user_id))
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

def cleanup_user_dir(user_id: int) -> None:
    """Clean up user's download directory."""
    try:
        user_dir = os.path.join(DOWNLOAD_DIR, str(user_id))
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
    except Exception as e:
        print(f"Cleanup error for user {user_id}: {str(e)}")

# Create main downloads directory if it doesn't exist
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR) 