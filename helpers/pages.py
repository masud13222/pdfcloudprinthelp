from pyrogram import Client, filters
from pyrogram.types import Message
import os
import fitz
import time
from PIL import Image
import io

# Import helpers
from .state import status_messages, user_states, PDFMerger, last_progress_update
from .progress import progress, edit_or_reply
from .constants import DOWNLOAD_DIR

async def pages_command(client: Client, message: Message):
    """Handle /pages command to show PDF info and first page preview."""
    try:
        user_id = message.from_user.id
        
        # Check if command is a reply to a PDF file
        if not message.reply_to_message or not message.reply_to_message.document or \
           not message.reply_to_message.document.file_name.lower().endswith('.pdf'):
            await message.reply_text(
                "❌ **দয়া করে একটি PDF ফাইলে রিপ্লাই দিয়ে /pages কমান্ড দিন।**\n\n"
                "**🔍 তথ্য পাবেন:**\n"
                "• PDF এর নাম\n"
                "• মোট পেজ সংখ্যা\n"
                "• প্রথম পেজের প্রিভিউ"
            )
            return
            
        # Initialize state
        if user_id in user_states:
            if user_id in status_messages:
                try:
                    await status_messages[user_id].delete()
                except:
                    pass
                del status_messages[user_id]
            user_states[user_id].reset()
            del user_states[user_id]
            
        user_states[user_id] = PDFMerger()
        
        # Create user-specific directory
        user_download_dir = os.path.join(DOWNLOAD_DIR, str(user_id))
        if not os.path.exists(user_download_dir):
            os.makedirs(user_download_dir)
            
        input_path = os.path.join(user_download_dir, "input.pdf")
        preview_path = os.path.join(user_download_dir, "preview.jpg")
        
        try:
            # Download PDF directly to disk
            start_time = time.time()
            await edit_or_reply(message, user_id, "📥 **PDF ডাউনলোড করা হচ্ছে...**")
            
            await message.reply_to_message.download(
                input_path,
                progress=progress,
                progress_args=(
                    message,
                    user_id,
                    "📥 **PDF ডাউনলোড করা হচ্ছে...**",
                    start_time
                )
            )
            
            # Get PDF info
            doc = fitz.open(input_path)
            total_pages = doc.page_count
            
            # Get first page preview
            first_page = doc[0]
            pix = first_page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
            
            # Convert to PIL and optimize
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=85, optimize=True)
            img_bytes.seek(0)
            
            # Close PDF
            doc.close()
            
            # Get file info
            file_name = message.reply_to_message.document.file_name
            file_size = message.reply_to_message.document.file_size / (1024 * 1024)  # MB
            
            # Send preview with info
            await message.reply_photo(
                photo=img_bytes,
                caption=(
                    "📄 **PDF তথ্য**\n\n"
                    f"**📋 নাম:** {file_name}\n"
                    f"**📚 মোট পেজ:** {total_pages}টি\n"
                    f"**📦 ফাইল সাইজ:** {file_size:.1f} MB\n\n"
                    "**🔍 প্রিভিউ:** প্রথম পেজ"
                )
            )
            
        except Exception as e:
            raise e
            
        finally:
            # Cleanup
            try:
                if os.path.exists(user_download_dir):
                    for file in os.listdir(user_download_dir):
                        os.remove(os.path.join(user_download_dir, file))
                    os.rmdir(user_download_dir)
            except:
                pass
                
            # Clean up state
            if user_id in status_messages:
                try:
                    await status_messages[user_id].delete()
                except:
                    pass
                del status_messages[user_id]
            if user_id in user_states:
                user_states[user_id].reset()
                del user_states[user_id]
            if user_id in last_progress_update:
                del last_progress_update[user_id]
                
    except Exception as e:
        # Clean up state on error
        if user_id in user_states:
            user_states[user_id].reset()
            del user_states[user_id]
        if user_id in status_messages:
            try:
                await status_messages[user_id].delete()
            except:
                pass
            del status_messages[user_id]
        if user_id in last_progress_update:
            del last_progress_update[user_id]
            
        await message.reply_text(
            "❌ **এরর!**\n\n"
            f"কারণ: {str(e)}\n"
            "দয়া করে আবার চেষ্টা করুন।"
        ) 