from pyrogram import Client, filters
from pyrogram.types import Message
import os
import PyPDF2
import tempfile
import time
import humanize
import asyncio
from typing import Dict, List

# Import state from state.py
from .state import user_states, status_messages, message_locks, last_progress_update, PDFMerger

# Constants
MAX_FILES = 20  # Maximum number of files
MAX_FILE_SIZE = 60 * 1024 * 1024  # 60MB per file
MAX_MERGED_SIZE = 1024 * 1024 * 1024  # 1GB merged file
UPDATE_INTERVAL = 10  # Update progress every 10 seconds

def get_status_text(merger: PDFMerger, current=0, total=0, start_time=None, file_num=None, total_files=None, status="waiting") -> str:
    """Generate status message text."""
    if status == "waiting":
        files_received = len(merger.pdf_files)
        files_remaining = merger.required_files - files_received
        return (
            f"📑 **PDF স্ট্যাটাস**\n\n"
            f"• গৃহীত: {files_received}টি PDF\n"
            f"• বাকি: {files_remaining}টি PDF\n"
            "• অপেক্ষমান..."
        )
    
    if status == "merging":
        return "🔄 **PDF ফাইলগুলি একত্রিত করা হচ্ছে...**"
    
    if status == "uploading":
        return "📤 **একত্রিত PDF ফাইল পাঠানো হচ্ছে...**"
        
    if status == "downloading":
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
        
        return (
            f"📥 **ডাউনলোড হচ্ছে: {file_num}/{total_files}**\n\n"
            f"{progress_bar} {percentage:.1f}%\n"
            f"⚡ স্পীড: {humanize.naturalsize(speed)}/s\n"
            f"⏱️ বাকি সময়: {humanize.naturaltime(eta, future=True)}"
        )
    
    return "⏳ **প্রসেস করা হচ্ছে...**"

async def update_status(message: Message, merger: PDFMerger, current=0, total=0, start_time=None, file_num=None, total_files=None, status="waiting"):
    """Update status message."""
    try:
        user_id = message.from_user.id
        status_text = get_status_text(merger, current, total, start_time, file_num, total_files, status)
        
        if status in ["downloading", "uploading"]:
            # For progress updates, edit existing message
            if user_id in status_messages:
                try:
                    await status_messages[user_id].edit_text(status_text)
                    return
                except Exception as e:
                    print(f"Failed to edit message: {str(e)}")
        else:
            # For status changes, delete old and create new
            if user_id in status_messages:
                try:
                    await status_messages[user_id].delete()
                except:
                    pass
                del status_messages[user_id]
        
        # Create new message if needed
        if user_id not in status_messages:
            status_messages[user_id] = await message.reply_text(status_text)
            
    except Exception as e:
        print(f"Status update error: {str(e)}")

async def progress(current: int, total: int, message: Message, text: str, start_time: float, file_num=None, total_files=None):
    """Update progress with rate limiting."""
    try:
        user_id = message.from_user.id
        now = time.time()
        
        # Update only if enough time has passed
        if user_id in user_states and (user_id not in last_progress_update or (now - last_progress_update.get(user_id, 0)) >= UPDATE_INTERVAL):
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
            
            if text == "Downloading":
                status_text = (
                    f"📥 **ডাউনলোড হচ্ছে: {file_num}/{total_files}**\n\n"
                    f"{progress_bar} {percentage:.1f}%\n"
                    f"⚡ স্পীড: {humanize.naturalsize(speed)}/s\n"
                    f"⏱️ বাকি সময়: {humanize.naturaltime(eta, future=True)}"
                )
            else:
                status_text = (
                    "📤 **আপলোড হচ্ছে**\n\n"
                    f"{progress_bar} {percentage:.1f}%\n"
                    f"⚡ স্পীড: {humanize.naturalsize(speed)}/s\n"
                    f"⏱️ বাকি সময়: {humanize.naturaltime(eta, future=True)}"
                )
            
            # Update status message
            if user_id in status_messages:
                try:
                    await status_messages[user_id].edit_text(status_text)
                except Exception as e:
                    print(f"Failed to update progress: {str(e)}")
            
    except Exception as e:
        print(f"Progress update error: {str(e)}")

async def merge_command(client: Client, message: Message):
    """Handle /merge command."""
    try:
        user_id = message.from_user.id
        
        # Check if user has an active download
        current_time = time.time()
        if user_id in last_progress_update and (current_time - last_progress_update[user_id]) < UPDATE_INTERVAL:
            await message.reply_text("❌ একটি মার্জ টাস্ক চলমান আছে। দয়া করে এটি শেষ হওয়ার অপেক্ষা করুন অথবা /allcancel দিয়ে বাতিল করুন।")
            return
        
        # Get number of PDFs to merge
        cmd = message.text.split()
        if len(cmd) != 2:
            await message.reply_text(
                "📚 **PDF মার্জার - ব্যবহার নির্দেশিকা**\n\n"
                "**কমান্ড:** `/merge সংখ্যা`\n"
                "**উদাহরণ:** `/merge 3`\n\n"
                "**ব্যবহার পদ্ধতি:**\n"
                "1️⃣ প্রথমে /merge লিখুন, তারপর স্পেস দিয়ে কতগুলো PDF মার্জ করবেন সেই সংখ্যা লিখুন\n"
                "2️⃣ কমান্ড পাঠানোর পর বট আপনার PDF ফাইল গুলো চাইবে\n"
                "3️⃣ একে একে সব PDF ফাইল পাঠিয়ে দিন\n"
                "4️⃣ সব ফাইল পাঠানো হয়ে গেলে বট আপনাকে একটি মার্জ করা PDF দিবে\n\n"
                "**সীমাবদ্ধতা:**\n"
                f"• সর্বোচ্চ {MAX_FILES}টি PDF একসাথে মার্জ করা যাবে\n"
                f"• প্রতিটি PDF ফাইল {humanize.naturalsize(MAX_FILE_SIZE)} এর মধ্যে হতে হবে\n"
                f"• মার্জ করা ফাইলের সাইজ {humanize.naturalsize(MAX_MERGED_SIZE)} এর বেশি হতে পারবে না\n\n"
                "**অতিরিক্ত কমান্ড:**\n"
                "• /allcancel - মার্জ প্রসেস বাতিল করতে\n\n"
                "**টিপস:**\n"
                "• PDF ফাইল গুলো ক্রমানুসারে পাঠাবেন, একই ক্রমে মার্জ হবে\n"
                "• মার্জ করার আগে PDF ফাইল গুলো ভালোভাবে চেক করে নিন\n\n"
                "**📺 টিউটোরিয়াল দেখুন:**\n"
                "• https://www.youtube.com/shorts/ejnbUV0X9t0"
            )
            return
        
        num_pdfs = int(cmd[1])
        if num_pdfs <= 1:
            await message.reply_text("❌ কমপক্ষে ২টি PDF ফাইল নির্বাচন করুন।")
            return
            
        if num_pdfs > MAX_FILES:
            await message.reply_text(f"❌ সর্বোচ্চ {MAX_FILES}টি PDF ফাইল একত্রিত করা যাবে।")
            return
        
        # Initialize merger for user
        user_id = message.from_user.id
        if user_id in user_states:
            user_states[user_id].reset()
        
        user_states[user_id] = PDFMerger()
        merger = user_states[user_id]
        merger.required_files = num_pdfs
        merger.collecting = True
        
        await message.reply_text(
            f"📥 **{num_pdfs}টি PDF ফাইল পাঠান**\n\n"
            f"• প্রতিটি ফাইল সাইজ: {humanize.naturalsize(MAX_FILE_SIZE)} এর মধ্যে হতে হবে\n"
            "• /allcancel - বাতিল করতে"
        )
        
    except ValueError:
        await message.reply_text("❌ অনুগ্রহ করে একটি বৈধ সংখ্যা দিন।")

async def handle_pdf(client: Client, message: Message):
    """Handle incoming PDF files."""
    try:
        user_id = message.from_user.id
        
        if user_id not in user_states or not user_states[user_id].collecting:
            return
        
        merger = user_states[user_id]
        
        # Check if it's a PDF file
        if not message.document or not message.document.file_name.lower().endswith('.pdf'):
            await message.reply_text("❌ দয়া করে একটি PDF ফাইল পাঠান।")
            return
        
        if message.document.file_size > MAX_FILE_SIZE:
            await message.reply_text(
                f"❌ ফাইল সাইজ {humanize.naturalsize(MAX_FILE_SIZE)} এর বেশি হতে পারবে না।"
            )
            return
        
        # Get or create lock for this user
        if user_id not in message_locks:
            message_locks[user_id] = asyncio.Lock()
        
        # Process file under lock
        async with message_locks[user_id]:
            # Add file to queue
            merger.pdf_files.append({
                'message': message,
                'name': message.document.file_name,
                'size': message.document.file_size
            })
            
            # Update status message
            await update_status(message, merger)
            
            # If all files received, start processing
            if len(merger.pdf_files) == merger.required_files:
                merger.collecting = False
                
                try:
                    # Download all PDFs
                    total_size = sum(f['size'] for f in merger.pdf_files)
                    
                    for i, pdf in enumerate(merger.pdf_files, 1):
                        # Check if operation was cancelled
                        if user_id not in user_states:
                            return
                            
                        file_path = os.path.join(merger.temp_dir, f"pdf_{i}.pdf")
                        temp_path = f"{file_path}.temp"
                        
                        # Download to temp file first
                        await pdf['message'].download(
                            temp_path,
                            progress=progress,
                            progress_args=(
                                message,
                                "Downloading",
                                time.time(),
                                i,
                                merger.required_files
                            )
                        )
                        
                        # Check if operation was cancelled
                        if user_id not in user_states:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                            return
                        
                        # Move temp file to final location
                        try:
                            os.replace(temp_path, file_path)
                            merger.downloaded_files.append(file_path)
                        except Exception as e:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                            raise Exception(f"ফাইল মুভ করতে সমস্যা: {str(e)}")
                    
                    # Check if operation was cancelled
                    if user_id not in user_states:
                        return
                    
                    # Merge PDFs
                    await update_status(message, merger, status="merging")
                    merge_start = time.time()
                    
                    output_path = os.path.join(merger.temp_dir, "merged.pdf")
                    temp_output = f"{output_path}.temp"
                    
                    # Check if operation was cancelled
                    if user_id not in user_states:
                        return
                    
                    # Merge to temp file first
                    merger_pdf = PyPDF2.PdfMerger()
                    for pdf_file in merger.downloaded_files:
                        # Check if operation was cancelled
                        if user_id not in user_states:
                            if os.path.exists(temp_output):
                                os.remove(temp_output)
                            return
                            
                        try:
                            merger_pdf.append(pdf_file)
                        except Exception as e:
                            raise Exception(f"PDF মার্জ করতে সমস্যা: {str(e)}")
                    
                    # Check if operation was cancelled
                    if user_id not in user_states:
                        if os.path.exists(temp_output):
                            os.remove(temp_output)
                        return
                    
                    merger_pdf.write(temp_output)
                    merger_pdf.close()
                    
                    # Check if operation was cancelled
                    if user_id not in user_states:
                        if os.path.exists(temp_output):
                            os.remove(temp_output)
                        return
                    
                    # Move merged file to final location
                    os.replace(temp_output, output_path)
                    
                    merge_time = time.time() - merge_start
                    
                    # Check merged file size
                    if os.path.getsize(output_path) > MAX_MERGED_SIZE:
                        await update_status(
                            message,
                            merger,
                            status=f"❌ একত্রিত ফাইলের সাইজ {humanize.naturalsize(MAX_MERGED_SIZE)} এর বেশি হতে পারবে না।"
                        )
                        merger.reset()
                        return
                    
                    # Check if operation was cancelled
                    if user_id not in user_states:
                        return
                    
                    # Send merged file
                    await update_status(message, merger, status="uploading")
                    
                    upload_start = time.time()
                    # Create file list with serial numbers
                    file_list = "\n".join([f"{i}. {pdf['name']}" for i, pdf in enumerate(merger.pdf_files, 1)])
                    
                    # Check if operation was cancelled
                    if user_id not in user_states:
                        return
                    
                    await message.reply_document(
                        document=output_path,
                        caption=(
                            "✅ PDF ফাইল একত্রিত করা হয়েছে!\n\n"
                            f"{file_list}\n\n"
                            f"• মোট ফাইল: {len(merger.downloaded_files)}টি\n"
                            f"• মোট সাইজ: {humanize.naturalsize(total_size)}\n"
                            f"• প্রসেস টাইম: {merge_time:.1f}s"
                        ),
                        progress=progress,
                        progress_args=(
                            message,
                            "Uploading",
                            upload_start
                        )
                    )
                    
                except Exception as e:
                    raise e
                finally:
                    # Clean up
                    if user_id in status_messages:
                        try:
                            await status_messages[user_id].delete()
                        except:
                            pass
                        del status_messages[user_id]
                    if user_id in message_locks:
                        del message_locks[user_id]
                    if user_id in user_states:
                        merger.reset()
        
    except Exception as e:
        print(f"PDF handling error: {str(e)}")
        if user_id in user_states:
            user_states[user_id].reset()
            del user_states[user_id]
        if user_id in status_messages:
            try:
                await status_messages[user_id].delete()
            except:
                pass
            del status_messages[user_id]
        if user_id in message_locks:
            del message_locks[user_id]
        await message.reply_text(
            "❌ **এরর!**\n\n"
            f"কারণ: {str(e)}\n"
            "দয়া করে আবার চেষ্টা করুন।"
        )
