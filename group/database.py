from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB setup
mongo_client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
db = mongo_client[os.getenv('DB_NAME')]
users_collection = db['users']

# Force sub channel
FORCE_SUB_CHANNEL = os.getenv('FORCE_SUB_CHANNEL')

async def check_subscription(client: Client, user_id: int) -> bool:
    """Check if user is subscribed to force sub channel."""
    try:
        member = await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return True
    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"Error checking subscription: {str(e)}")
        return True  # Allow on error

async def force_sub_message():
    """Get force sub message with button."""
    button = [
        [InlineKeyboardButton(
            "📢 চ্যানেলে জয়েন করুন",
            url=f"https://t.me/{FORCE_SUB_CHANNEL.replace('@', '')}"
        )],
        [InlineKeyboardButton(
            "🔄 Try Again",
            callback_data="checksub"
        )]
    ]
    
    text = (
        "❌ **দুঃখিত! আপনি আমাদের চ্যানেলের সদস্য নন।**\n\n"
        "বট ব্যবহার করতে আমাদের চ্যানেলে জয়েন করুন।\n"
        "জয়েন করার পর 'Try Again' বাটনে ক্লিক করুন।\n"
        "**📺 টিউটোরিয়াল দেখুন:**\n"
        "• https://www.youtube.com/watch?v=a35aefCCJTY"
    )
    
    return text, InlineKeyboardMarkup(button)

async def add_user(message: Message):
    """Add new user to database."""
    try:
        user = message.from_user
        
        # Check if user exists
        if not await users_collection.find_one({"user_id": user.id}):
            # Add new user
            user_data = {
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "joined_date": datetime.utcnow(),
                "last_used": datetime.utcnow()
            }
            await users_collection.insert_one(user_data)
        else:
            # Update last used
            await users_collection.update_one(
                {"user_id": user.id},
                {"$set": {"last_used": datetime.utcnow()}}
            )
            
    except Exception as e:
        print(f"Error adding user: {str(e)}")

async def start_command(client: Client, message: Message):
    """Handle /start command."""
    try:
        # Check force subscription
        if not await check_subscription(client, message.from_user.id):
            text, markup = await force_sub_message()
            await message.reply_text(
                text,
                reply_markup=markup,
                disable_web_page_preview=True
            )
            return
        
        # Add user to database
        await add_user(message)
        
        # Send welcome message
        await message.reply_text(
            "👋 **স্বাগতম!**\n"
            "**CloudPrint Team** এর PDF হেল্পার বটে আপনাকে স্বাগতম।\n\n"
            "**📚 কমান্ড সমূহ:**\n\n"
            "**🔰 PDF টুলস:**\n"
            "• /merge - একাধিক PDF একত্রে জোড়া\n"
            "• /invert - PDF এর ডার্ক পেজ ইনভার্ট\n"
            "• /inverts - স্মার্ট ইনভার্ট + খালি পেজ রিমুভ\n"
            "• /invertsexp - এক্সপেরিমেন্টাল স্মার্ট ইনভার্ট\n"
            "• /pages - PDF এর পেজ সংখ্যা ও প্রিভিউ\n"
            "• /pdf - গুগল ড্রাইভ লিংক থেকে PDF\n\n"
            "**💰 প্রিন্টিং টুলস:**\n"
            "• /price - প্রিন্টিং মূল্য হিসাব\n\n"
            "**⚙️ অন্যান্য কমান্ড:**\n"
            "• /allcancel - চলমান কাজ বাতিল\n\n"
            "**🔍 বিশেষ দ্রষ্টব্য:**\n"
            "• PDF ফাইল পাঠানোর পর কমান্ড দিন\n"
            "• একবারে একটি কমান্ড ব্যবহার করুন\n"
            "• বড় ফাইলের ক্ষেত্রে কিছুটা সময় লাগবে\n\n"
            "**👥 সহযোগিতায়:**\n"
            "• @cloudprintonline\n\n"
            "**📺 টিউটোরিয়াল দেখুন:**\n"
            "• https://www.youtube.com/watch?v=a35aefCCJTY",
            disable_web_page_preview=True
        )
            
    except Exception as e:
        print(f"Error in start command: {str(e)}")
        await message.reply_text(
            "❌ **দুঃখিত! একটি সমস্যা হয়েছে।**\n\n"
            "দয়া করে আবার চেষ্টা করুন।"
        )

async def handle_force_sub_callback(client: Client, callback: CallbackQuery):
    """Handle force sub callback."""
    try:
        if callback.data != "checksub":
            return
            
        if not await check_subscription(client, callback.from_user.id):
            await callback.answer("আপনি এখনও চ্যানেলে জয়েন করেননি!", show_alert=True)
            text, markup = await force_sub_message()
            await callback.message.edit_text(text, reply_markup=markup)
            return
            
        # User has joined, show start message
        await callback.message.delete()
        await start_command(client, callback.message)
    except Exception as e:
        print(f"Error handling force sub callback: {str(e)}") 