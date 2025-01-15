from pyrogram import Client, filters
from pyrogram.types import Message
import os
import tempfile
import time
import fitz
import numpy as np
from PIL import Image
import io
import humanize

# Import state management
from .state import status_messages, user_states, PDFMerger, last_progress_update
from .cancel import cancel_command

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
        if user_id not in user_states:
            return
        
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

async def invert_command(client: Client, message: Message):
    """Handle /invert command on PDF files."""
    try:
        user_id = message.from_user.id
        
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
                "3️⃣ প্রসেস শেষ হওয়া পর্যন্ত অপেক্ষা করুন"
            )
            return
        
        # Initialize state for user
        if user_id in user_states:
            await cancel_command(client, message)
        user_states[user_id] = PDFMerger()
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, "input.pdf")
        output_path = os.path.join(temp_dir, "inverted.pdf")
        
        try:
            # Download PDF
            start_time = time.time()
            await edit_or_reply(message, user_id, "📥 **PDF ডাউনলোড করা হচ্ছে...**")
            
            # Check if cancelled
            if user_id not in user_states:
                return
                
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
            if user_id not in user_states:
                return
            
            # Open PDF
            doc = fitz.open(input_path)
            out_pdf = fitz.open()
            
            # Copy metadata
            out_pdf.metadata = doc.metadata
            
            # Process pages
            total_pages = doc.page_count
            inverted_count = 0
            for page_num in range(total_pages):
                # Check if cancelled
                if user_id not in user_states:
                    doc.close()
                    out_pdf.close()
                    return
                
                # Update status
                await edit_or_reply(
                    message, 
                    user_id,
                    f"🔄 **PDF প্রসেস করা হচ্ছে...**\n\n"
                    f"• পেজ: {page_num + 1}/{total_pages}\n"
                    f"• ইনভার্টেড: {inverted_count}টি"
                )
                
                page = doc[page_num]
                
                # Get pixmap with optimized resolution
                zoom = 1.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Convert to numpy array for faster processing
                img_array = np.frombuffer(pix.samples, dtype=np.uint8)
                img_array = img_array.reshape(pix.height, pix.width, 3)
                
                # Quick check for dark background
                is_dark = np.mean(img_array) < 128
                
                if is_dark:
                    # Fast inversion
                    img_array = 255 - img_array
                    inverted_count += 1
                    
                    # Convert to bytes
                    img = Image.fromarray(img_array)
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format='JPEG', quality=85, optimize=True)
                    
                    # Create new page
                    new_page = out_pdf.new_page(width=page.rect.width,
                                              height=page.rect.height)
                    
                    # Insert inverted image
                    new_page.insert_image(page.rect, 
                                        stream=img_bytes.getvalue(),
                                        keep_proportion=True)
                else:
                    # Copy original page if not dark
                    out_pdf.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            # Check if cancelled
            if user_id not in user_states:
                doc.close()
                out_pdf.close()
                return
            
            # Save optimized PDF
            await edit_or_reply(message, user_id, "📄 **ইনভার্টেড PDF সেভ করা হচ্ছে...**")
            out_pdf.save(output_path,
                        garbage=4,
                        deflate=True,
                        clean=True,
                        linear=True)
            
            # Close documents
            doc.close()
            out_pdf.close()
            
            # Send inverted PDF
            start_time = time.time()
            await edit_or_reply(message, user_id, "📤 **ইনভার্টেড PDF পাঠানো হচ্ছে...**")
            
            # Check if cancelled
            if user_id not in user_states:
                return
            
            # Get file stats
            orig_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
            new_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            
            original_name = message.reply_to_message.document.file_name
            inverted_name = f"inverted_{original_name}"
            
            await message.reply_document(
                document=output_path,
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
            # Clean up temp files
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rmdir(temp_dir)
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
