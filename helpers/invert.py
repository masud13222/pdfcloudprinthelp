from pyrogram import Client, filters
from pyrogram.types import Message
import os
import time
import fitz
import numpy as np
from PIL import Image
import io
import humanize
import asyncio

# Import state management
from .state import status_messages, user_states, PDFMerger, last_progress_update
from .cancel import cancel_command
from .constants import DOWNLOAD_DIR

# Create downloads directory if it doesn't exist
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

async def edit_or_reply(message: Message, user_id: int, text: str):
    """Edit existing status message or send new one."""
    try:
        if user_id in status_messages:
            try:
                await status_messages[user_id].edit_text(text)
                return
            except Exception as e:
                print(f"Edit error: {str(e)}")
        
        # If edit fails or no message exists, send new
        status_messages[user_id] = await message.reply_text(text)
            
    except Exception as e:
        print(f"Status update error: {str(e)}")

async def progress(current: int, total: int, message: Message, user_id: int, text: str, start_time: float):
    """Update progress with rate limiting."""
    try:
        now = time.time()
        
        # Check if operation was cancelled
        if user_id not in user_states or not user_states[user_id].collecting:
            # Force stop download by raising exception
            raise asyncio.CancelledError("Download cancelled")
        
        # Update only if enough time has passed (5 seconds)
        if user_id not in last_progress_update or (now - last_progress_update.get(user_id, 0)) >= 5.0:
            last_progress_update[user_id] = now
            
            # Calculate progress
            percentage = (current * 100) / total if total > 0 else 0
            elapsed_time = time.time() - start_time if start_time else 0
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
            
    except Exception as e:
        print(f"Progress update error: {str(e)}")
        if isinstance(e, asyncio.CancelledError):
            raise  # Re-raise CancelledError to stop download
    
    except Exception as e:
        print(f"Progress update error: {str(e)}")

async def invert_command(client: Client, message: Message):
    """Handle /invert command on PDF files."""
    try:
        user_id = message.from_user.id
        
        # Initialize state for user
        if user_id in user_states:
            await cancel_command(client, message)
        user_states[user_id] = PDFMerger()
        user_states[user_id].collecting = True  # Mark as processing
        
        # Check if command is a reply to a PDF file
        if not message.reply_to_message or not message.reply_to_message.document or \
           not message.reply_to_message.document.file_name.lower().endswith('.pdf'):
            await message.reply_text(
                "❌ **দয়া করে একটি PDF ফাইলে রিপ্লাই দিয়ে /invert কমান্ড দিন।**\n\n"
                "**📝 ফিচারসমূহ:**\n"
                "• ডার্ক পেজগুলো স্বয়ংক্রিয়ভাবে ইনভার্ট হবে\n"
                "• লাইট পেজগুলো আগের মতই থাকবে\n\n"
                "**🔄 ব্যবহার পদ্ধতি:**\n"
                "1️⃣ PDF ফাইলটি পাঠান\n"
                "2️⃣ ফাইলে রিপ্লাই দিয়ে /invert কমান্ড দিন\n"
                "3️⃣ প্রসেস শেষ হওয়া পর্যন্ত অপেক্ষা করুন\n\n"
                "**📺 টিউটোরিয়াল দেখুন:**\n"
                "• https://www.youtube.com/shorts/WlYxu2pkKRI"
            )
            return
        
        # Create user-specific directory
        user_download_dir = os.path.join(DOWNLOAD_DIR, str(user_id))
        if not os.path.exists(user_download_dir):
            os.makedirs(user_download_dir)
            
        input_path = os.path.join(user_download_dir, "input.pdf")
        temp_path = os.path.join(user_download_dir, "temp.pdf")
        output_path = os.path.join(user_download_dir, "inverted.pdf")
        
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
            
            # Check if cancelled
            if user_id not in user_states or not user_states[user_id].collecting:
                return
            
            # Process PDF in batches of 15 pages
            doc = fitz.open(input_path)
            total_pages = doc.page_count
            inverted_count = 0
            batch_size = 15
            
            # Create output path for final merged PDF
            final_output = os.path.join(user_download_dir, "output.pdf")
            
            for batch_start in range(0, total_pages, batch_size):
                # Check if cancelled
                if user_id not in user_states or not user_states[user_id].collecting:
                    return
                    
                batch_end = min(batch_start + batch_size, total_pages)
                
                # Update status
                await edit_or_reply(
                    message,
                    user_id,
                    f"🔄 **PDF প্রসেস করা হচ্ছে...**\n\n"
                    f"• পেজ: {batch_start + 1}-{batch_end}/{total_pages}\n"
                    f"• ইনভার্টেড: {inverted_count}টি"
                )
                
                # Create PDF for current batch
                batch_pdf = fitz.open()
                
                # Process batch
                for page_num in range(batch_start, batch_end):
                    # Check if cancelled
                    if user_id not in user_states or not user_states[user_id].collecting:
                        return
                        
                    page = doc[page_num]
                    
                    # Get pixmap
                    pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
                    
                    # Convert to numpy array
                    img_array = np.frombuffer(pix.samples, dtype=np.uint8)
                    img_array = img_array.reshape(pix.height, pix.width, 3)
                    
                    # Check if dark
                    is_dark = np.mean(img_array) < 128
                    
                    if is_dark:
                        # Invert colors
                        img_array = 255 - img_array
                        inverted_count += 1
                        
                        # Save to PDF
                        img = Image.fromarray(img_array)
                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format='JPEG', quality=85, optimize=True)
                        
                        new_page = batch_pdf.new_page(width=page.rect.width,
                                                    height=page.rect.height)
                        new_page.insert_image(page.rect, 
                                            stream=img_bytes.getvalue(),
                                            keep_proportion=True)
                    else:
                        # Copy original page
                        batch_pdf.insert_pdf(doc, from_page=page_num, to_page=page_num)
                
                # Save batch to disk
                batch_path = os.path.join(user_download_dir, f"batch_{batch_start}.pdf")
                batch_pdf.save(batch_path, garbage=4, deflate=True)
                batch_pdf.close()
                
                # If this is first batch, copy it as base for final output
                if batch_start == 0:
                    os.rename(batch_path, final_output)
                else:
                    # Append batch to final output using a temporary file
                    temp_output = os.path.join(user_download_dir, "temp_output.pdf")
                    
                    # Create new PDF with all pages
                    with fitz.open() as new_pdf:
                        # Copy pages from existing output
                        new_pdf.insert_pdf(fitz.open(final_output))
                        # Add new batch pages
                        new_pdf.insert_pdf(fitz.open(batch_path))
                        # Save to temp file
                        new_pdf.save(temp_output, garbage=4, deflate=True, clean=True)
                    
                    # Replace old output with new
                    os.remove(final_output)
                    os.rename(temp_output, final_output)
                
                # Remove batch file
                if os.path.exists(batch_path):
                    os.remove(batch_path)
            
            # Close input document
            doc.close()
            
            # Check if cancelled
            if user_id not in user_states or not user_states[user_id].collecting:
                return
            
            # Send inverted PDF
            start_time = time.time()
            await edit_or_reply(message, user_id, "📤 **ইনভার্টেড PDF পাঠানো হচ্ছে...**")
            
            # Get file stats
            orig_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
            new_size = os.path.getsize(final_output) / (1024 * 1024)  # MB
            
            original_name = message.reply_to_message.document.file_name
            inverted_name = f"inverted_{original_name}"
            
            await message.reply_document(
                document=final_output,
                file_name=inverted_name,
                caption=(
                    "✅ **PDF ইনভার্ট করা হয়েছে!**\n\n"
                    f"• অরিজিনাল ফাইল: {original_name}\n"
                    f"• মোট পেজ: {total_pages}টি\n"
                    f"• অনভার্টেড: {inverted_count}টি\n"
                    f"• অরিজিনাল সাইজ: {orig_size:.1f} MB\n"
                    f"• নতুন সাইজ: {new_size:.1f} MB"
                ),
                progress=progress,
                progress_args=(
                    message,
                    user_id,
                    "📤 **ইনভার্টেড PDF পাঠানো হচ্ছে...**",
                    start_time
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
            
            # Clear user state
            if user_id in user_states:
                user_states[user_id].collecting = False
                del user_states[user_id]
            
            # Clean up state
            if user_id in status_messages:
                try:
                    await status_messages[user_id].delete()
                except:
                    pass
                del status_messages[user_id]
            if user_id in last_progress_update:
                del last_progress_update[user_id]
    
    except Exception as e:
        # Clean up state on error
        if user_id in user_states:
            user_states[user_id].collecting = False
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
