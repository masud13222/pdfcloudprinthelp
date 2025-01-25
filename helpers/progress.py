from pyrogram.types import Message
import time
import humanize
import asyncio
from typing import Dict, Optional

# Store status messages
status_messages: Dict[int, Message] = {}
last_progress_update: Dict[int, float] = {}

async def edit_or_reply(message: Message, user_id: int, text: str) -> Optional[Message]:
    """Edit existing status message or send new one."""
    try:
        if user_id in status_messages:
            try:
                await status_messages[user_id].edit_text(text)
                return status_messages[user_id]
            except Exception as e:
                print(f"Edit error: {str(e)}")
        
        # If edit fails or no message exists, send new
        status_messages[user_id] = await message.reply_text(text)
        return status_messages[user_id]
            
    except Exception as e:
        print(f"Status update error: {str(e)}")
        return None

async def update_progress(
    current: int,
    total: int,
    message: Message,
    user_id: int,
    text: str,
    start_time: float
) -> None:
    """Update progress with rate limiting."""
    try:
        from .db import is_process_running
        
        now = time.time()
        
        # Check if process was cancelled
        if not await is_process_running(user_id):
            raise asyncio.CancelledError("Process cancelled")
        
        # Update only if enough time has passed (5 seconds)
        if user_id not in last_progress_update or (now - last_progress_update.get(user_id, 0)) >= 5.0:
            last_progress_update[user_id] = now
            
            # Calculate progress
            percentage = (current * 100) / total if total > 0 else 0
            elapsed_time = now - start_time if start_time else 0
            speed = current / elapsed_time if elapsed_time > 0 else 0
            eta = (total - current) / speed if speed > 0 else 0
            
            # Generate progress bar
            progress_bar = "".join(
                "█" if i <= percentage / 5 else "░"
                for i in range(20)
            )
            
            status_text = (
                f"{text}\n\n"
                f"{progress_bar} {percentage:.1f}%\n"
                f"⚡ স্পীড: {humanize.naturalsize(speed)}/s\n"
                f"⏱️ বাকি সময়: {humanize.naturaltime(eta, future=True)}"
            )
            
            await edit_or_reply(message, user_id, status_text)
            
    except asyncio.CancelledError:
        raise  # Re-raise to cancel operation
    except Exception as e:
        print(f"Progress update error: {str(e)}")

async def cleanup_status(user_id: int) -> None:
    """Clean up status message and progress tracking."""
    try:
        if user_id in status_messages:
            try:
                await status_messages[user_id].delete()
            except:
                pass
            del status_messages[user_id]
            
        if user_id in last_progress_update:
            del last_progress_update[user_id]
    except Exception as e:
        print(f"Status cleanup error: {str(e)}") 