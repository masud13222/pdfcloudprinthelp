from pyrogram import Client, filters
from pyrogram.types import Message
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB setup
mongo_client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
db = mongo_client[os.getenv('DB_NAME')]
users_collection = db['users']

# Get admin IDs from env
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

async def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in ADMIN_IDS

async def users_command(client: Client, message: Message):
    """Handle /users command to show user statistics."""
    try:
        # Check if user is admin
        if not await is_admin(message.from_user.id):
            await message.reply_text(
                "❌ **অননুমোদিত অ্যাক্সেস!**\n\n"
                "শুধুমাত্র অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।"
            )
            return
            
        # Get user stats from MongoDB
        total_users = await users_collection.count_documents({})
        today_users = await users_collection.count_documents({
            "joined_date": {
                "$gte": {"$date": {"$now": {"$subtract": ["$$NOW", 24*60*60*1000]}}}
            }
        })
        
        # Get active users (used bot in last 24h)
        active_users = await users_collection.count_documents({
            "last_used": {
                "$gte": {"$date": {"$now": {"$subtract": ["$$NOW", 24*60*60*1000]}}}
            }
        })
        
        await message.reply_text(
            "📊 **ব্যবহারকারী পরিসংখ্যান**\n\n"
            f"👥 **মোট ব্যবহারকারী:** {total_users:,}জন\n"
            f"📅 **আজকের নতুন:** {today_users:,}জন\n"
            f"✨ **২৪ ঘন্টায় সক্রিয়:** {active_users:,}জন\n\n"
            "**📝 নোট:** শুধুমাত্র অ্যাডমিনরা এই তথ্য দেখতে পারবেন।"
        )
            
    except Exception as e:
        await message.reply_text(
            "❌ **এরর!**\n\n"
            f"কারণ: {str(e)}\n"
            "দয়া করে আবার চেষ্টা করুন।"
        ) 