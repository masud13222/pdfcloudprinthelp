from pyrogram import Client, filters
from pyrogram.types import Message
import os
import tempfile
import time
import re
import requests
import img2pdf
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

def extract_drive_id(url: str) -> str:
    """Extract Google Drive file ID from URL."""
    patterns = [
        r"https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
        r"https://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
        r"^([a-zA-Z0-9_-]+)$"  # Direct ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def drive_command(client: Client, message: Message):
    """Handle /pdf command for Google Drive PDF download."""
    try:
        user_id = message.from_user.id
        
        # Check command format
        command_parts = message.text.split(" ", 1)
        if len(command_parts) != 2:
            await message.reply_text(
                "🔰 **Google Drive PDF ডাউনলোডার**\n\n"
                "**📝 ফিচারসমূহ:**\n"
                "• Google Drive থেকে PDF ডাউনলোড করা\n"
                "• রিয়েল-টাইম প্রগ্রেস আপডেট\n"
                "• স্বয়ংক্রিয়ভাবে ফাইল নাম ডিটেকশন\n"
                "• অপটিমাইজড ইমেজ কোয়ালিটি\n"
                "• ফাইল সাইজ অপটিমাইজেশন\n\n"
                "**🔄 ব্যবহার পদ্ধতি:**\n"
                "1️⃣ Google Drive এ PDF ফাইলটি ওপেন করুন\n"
                "2️⃣ শেয়ার লিংক কপি করুন বা ফাইল ID কপি করুন\n"
                "3️⃣ নিচের যেকোনো একটি ফরম্যাটে কমান্ড দিন:\n"
                "   • `/pdf <ফাইল Drive Link>`\n"
                "4️⃣ প্রসেস শেষ হওয়া পর্যন্ত অপেক্ষা করুন\n\n"
                "**💡 উদাহরণ:**\n"
                "1️⃣ লিংক দিয়ে:\n"
                "`/pdf https://drive.google.com/file/d/abc123xyz/view`\n\n"
                "2️⃣ ফাইল ID দিয়ে:\n"
                "`/pdf abc123xyz`\n\n"
                "**⚠️ গুরুত্বপূর্ণ:**\n"
                "• PDF ফাইলটি অবশ্যই পাবলিক শেয়ার করা থাকতে হবে\n"
                "• ফাইল সাইজ 2GB এর কম হতে হবে\n\n"
                "**📺 টিউটোরিয়াল দেখুন:**\n"
                "• https://www.youtube.com/shorts/Sa0iI8dTMdM"
            )
            return
        
        # Extract Drive ID
        drive_url = command_parts[1].strip()
        file_id = extract_drive_id(drive_url)
        
        if not file_id:
            await message.reply_text("❌ **ভুল Google Drive লিংক/ফাইল ID!**")
            return
        
        # Initialize state for user
        if user_id in user_states:
            user_states[user_id].reset()
        user_states[user_id] = PDFMerger()
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        images_dir = os.path.join(temp_dir, "images")
        os.makedirs(images_dir)
        output_path = os.path.join(temp_dir, "output.pdf")
        
        try:
            # Start session
            await edit_or_reply(message, user_id, "🔍 **Google Drive ফাইল চেক করা হচ্ছে...**")
            
            session = requests.Session()
            response = session.get(
                f'https://drive.google.com/file/d/{file_id}/view',
            )
            
            # Extract token and filename
            token_match = re.search(r"https://drive\.google\.com/viewer2/prod-\d{2}/meta\?ck\\u003ddrive\\u0026ds\\u003d(.+?)\",", response.text)
            name_match = re.search(r"itemJson: \[null,\"(.+?)\"", response.text)
            
            if not token_match or not name_match:
                await message.reply_text("❌ **Google Drive ফাইল অ্যাক্সেস করা যাচ্ছে না!**")
                return
            
            url_token = token_match[1]
            file_name = name_match[1][:-4]  # Remove .pdf
            
            # Download pages
            page_count = 0
            downloaded_size = 0
            start_time = time.time()
            
            for i in range(999):  # Max 999 pages
                # Check if cancelled
                if user_id not in user_states:
                    return
                
                # Download page
                image_url = f"https://drive.google.com/viewer2/prod-01/img?ck=drive&ds={url_token}&authuser=0&page={i}&skiphighlight=true&w=1600&webp=true"
                img_response = session.get(image_url)
                
                if img_response.status_code != 200:
                    break
                
                # Save page
                page_path = os.path.join(images_dir, f"{str(i).zfill(3)}.png")
                with open(page_path, "wb") as f:
                    f.write(img_response.content)
                
                # Update progress
                page_count = i + 1
                downloaded_size += len(img_response.content)
                
                # Update status every 5 seconds
                now = time.time()
                if user_id not in last_progress_update or (now - last_progress_update.get(user_id, 0)) >= 5.0:
                    last_progress_update[user_id] = now
                    
                    # Calculate speed and ETA
                    elapsed_time = now - start_time
                    speed = downloaded_size / elapsed_time if elapsed_time > 0 else 0
                    
                    await edit_or_reply(
                        message,
                        user_id,
                        f"📥 **পেজ ডাউনলোড করা হচ্ছে...**\n\n"
                        f"• ফাইল: {file_name}\n"
                        f"• পেজ: {page_count}টি\n"
                        f"• সাইজ: {humanize.naturalsize(downloaded_size)}\n"
                        f"• স্পীড: {humanize.naturalsize(speed)}/s"
                    )
            
            if page_count == 0:
                await message.reply_text("❌ **কোনো পেজ পাওয়া যায়নি!**")
                return
            
            # Convert to PDF
            await edit_or_reply(message, user_id, "📄 **PDF তৈরি করা হচ্ছে...**")
            
            # Get all images
            images = []
            for i in range(page_count):
                page_path = os.path.join(images_dir, f"{str(i).zfill(3)}.png")
                if os.path.exists(page_path):
                    images.append(page_path)
            
            # Convert to PDF
            with open(output_path, "wb") as f:
                f.write(img2pdf.convert(images))
            
            # Send PDF
            pdf_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            start_time = time.time()
            
            await edit_or_reply(message, user_id, "📤 **PDF পাঠানো হচ্ছে...**")
            
            await message.reply_document(
                document=output_path,
                file_name=f"{file_name}.pdf",
                caption=(
                    "✅ **Google Drive PDF ডাউনলোড করা হয়েছে!**\n\n"
                    f"• ফাইল: {file_name}.pdf\n"
                    f"• মোট পেজ: {page_count}টি\n"
                    f"• ফাইল সাইজ: {pdf_size:.1f} MB"
                ),
                progress=progress,
                progress_args=(
                    message,
                    user_id,
                    "📤 **PDF পাঠানো হচ্ছে...**",
                    start_time
                )
            )
            
        except Exception as e:
            raise e
        finally:
            # Clean up temp files
            try:
                if os.path.exists(images_dir):
                    for file in os.listdir(images_dir):
                        os.remove(os.path.join(images_dir, file))
                    os.rmdir(images_dir)
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