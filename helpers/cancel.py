from pyrogram import Client
from pyrogram.types import Message
from .downloads import cleanup_user_dir
from .progress import cleanup_status
from .db import end_process, get_user_process

async def cancel_command(client: Client, message: Message) -> None:
    """Cancel all ongoing operations for a user."""
    try:
        user_id = message.from_user.id
        
        # Check if user has ongoing process
        process = await get_user_process(user_id)
        if not process:
            await message.reply_text("❌ কোন চলমান প্রসেস নেই!")
            return
            
        # End process tracking
        await end_process(user_id)
        
        # Clean up downloads
        cleanup_user_dir(user_id)
        
        # Clean up status messages
        await cleanup_status(user_id)
        
        # Send confirmation
        await message.reply_text("✅ সকল চলমান কমান্ড বাতিল করা হয়েছে।")
        
    except Exception as e:
        await message.reply_text(
            "❌ **এরর!**\n\n"
            f"বাতিল করতে সমস্যা হয়েছে। কারণ: {str(e)}\n"
            "দয়া করে আবার চেষ্টা করুন।"
        ) 