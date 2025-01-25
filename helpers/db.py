from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any
import os

# MongoDB connection
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(MONGO_URL)
db = client.pdf_bot

# Collections
processes = db.processes  # Track ongoing processes

async def start_process(user_id: int, process_type: str, start_time: float) -> None:
    """Start tracking a new process for user."""
    await processes.update_one(
        {'user_id': user_id},
        {
            '$set': {
                'user_id': user_id,
                'process_type': process_type,
                'start_time': start_time,
                'status': 'running'
            }
        },
        upsert=True
    )

async def end_process(user_id: int) -> None:
    """End process tracking for user."""
    await processes.delete_one({'user_id': user_id})

async def get_user_process(user_id: int) -> Optional[Dict[str, Any]]:
    """Get ongoing process info for user."""
    return await processes.find_one({'user_id': user_id})

async def is_process_running(user_id: int) -> bool:
    """Check if user has any ongoing process."""
    process = await get_user_process(user_id)
    return process is not None 