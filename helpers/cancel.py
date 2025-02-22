from pyrogram import Client, filters
from pyrogram.types import Message
import os
import shutil

# Import state from state.py
from .state import user_states, status_messages, message_locks, last_progress_update

async def cancel_command(client: Client, message: Message):
    """Cancel all ongoing operations for a user."""
    try:
        user_id = message.from_user.id
        
        # First stop all ongoing processes
        if user_id in user_states:
            # Mark as not collecting to stop new files
            if hasattr(user_states[user_id], 'collecting'):
                user_states[user_id].collecting = False
            
            # Force stop any ongoing downloads/uploads
            if user_id in status_messages:
                try:
                    # Delete the status message to stop progress updates
                    await status_messages[user_id].delete()
                except:
                    pass
            
            # Clean up any temporary files that might be in use
            try:
                if hasattr(user_states[user_id], 'temp_dir'):
                    temp_dir = user_states[user_id].temp_dir
                    if temp_dir and os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            
            # Reset and clean up state
            if hasattr(user_states[user_id], 'reset'):
                user_states[user_id].reset()
            del user_states[user_id]
            
        # Remove progress tracking
        if user_id in last_progress_update:
            del last_progress_update[user_id]
            
        # Clean up status messages
        if user_id in status_messages:
            try:
                await status_messages[user_id].delete()
            except:
                pass
            del status_messages[user_id]
            
        # Clean up message locks
        if user_id in message_locks:
            del message_locks[user_id]
            
        # Send confirmation
        await message.reply_text("✅ সকল চলমান কমান্ড বাতিল করা হয়েছে।")
        
    except Exception as e:
        await message.reply_text(
            "❌ **এরর!**\n\n"
            f"বাতিল করতে সমস্যা হয়েছে। কারণ: {str(e)}\n"
            "দয়া করে আবার চেষ্টা করুন।"
        ) 