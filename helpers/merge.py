from pyrogram import Client, filters
from pyrogram.types import Message
import os
import pikepdf
import time
import humanize
import asyncio
from typing import List, Dict
import sys

# Import helpers
from .downloads import create_user_dir, cleanup_user_dir, DOWNLOAD_DIR
from .progress import update_progress, edit_or_reply, cleanup_status
from .db import start_process, end_process, is_process_running, get_user_process

# Constants
MAX_FILES = 20  # Maximum number of files
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB per file
MAX_MERGED_SIZE = 1024 * 1024 * 1024  # 1GB merged file
UPDATE_INTERVAL = 5  # Update progress every 5 seconds

sys.setrecursionlimit(10000)  # Increase recursion limit

# Store PDF files for each user
pdf_files_store: Dict[int, List['PDFFile']] = {}
required_files_store: Dict[int, int] = {}

# Type for storing PDF file info
class PDFFile:
    def __init__(self, message: Message, name: str, size: int):
        self.message = message
        self.name = name 
        self.size = size
        self.path = ""

async def get_status_text(
    user_id: int,
    current=0,
    total=0,
    start_time=None,
    file_num=None,
    total_files=None,
    status="waiting"
) -> str:
    """Generate status message text."""
    if status == "waiting":
        files_received = len(pdf_files_store.get(user_id, []))
        files_remaining = required_files_store.get(user_id, 0) - files_received
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
        return f"📥 **ডাউনলোড হচ্ছে: {file_num}/{total_files}**"
    
    return "⏳ **প্রসেস করা হচ্ছে...**"

async def merge_command(client: Client, message: Message):
    """Handle /merge command."""
    try:
        user_id = message.from_user.id
        
        # Check if already processing
        if await is_process_running(user_id):
            await message.reply_text(
                "❌ **একটি প্রসেস চলমান আছে!**\n\n"
                "দয়া করে আগের প্রসেস শেষ হওয়া পর্যন্ত অপেক্ষা করুন,\n"
                "অথবা /allcancel কমান্ড দিয়ে বর্তমান প্রসেস বাতিল করুন।"
            )
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
            
        # Start tracking process
        await start_process(user_id, "merge", time.time())
        
        # Initialize empty list for PDF files
        pdf_files_store[user_id] = []
        required_files_store[user_id] = num_pdfs
        
        await message.reply_text(
            f"📥 **{num_pdfs}টি PDF ফাইল পাঠান**\n\n"
            f"• প্রতিটি ফাইল সাইজ: {humanize.naturalsize(MAX_FILE_SIZE)} এর মধ্যে হতে হবে\n"
            "• /allcancel - বাতিল করতে"
        )
        
        # Create status message
        status_text = await get_status_text(user_id)
        await edit_or_reply(message, user_id, status_text)
        
    except ValueError:
        await message.reply_text("❌ অনুগ্রহ করে একটি বৈধ সংখ্যা দিন।")
    except Exception as e:
        await end_process(user_id)
        await message.reply_text(f"❌ এরর: {str(e)}")

async def handle_pdf(client: Client, message: Message):
    """Handle incoming PDF files."""
    try:
        user_id = message.from_user.id
        
        # Check if user has active merge process
        process = await get_user_process(user_id)
        if not process or process['process_type'] != 'merge':
            return
            
        # Check if it's a PDF file
        if not message.document or not message.document.file_name.lower().endswith('.pdf'):
            await message.reply_text("❌ দয়া করে একটি PDF ফাইল পাঠান।")
            return
        
        if message.document.file_size > MAX_FILE_SIZE:
            await message.reply_text(
                f"❌ ফাইল সাইজ {humanize.naturalsize(MAX_FILE_SIZE)} এর বেশি হতে পারবে না।"
            )
            return
            
        # Create PDF file object
        pdf_file = PDFFile(
            message=message,
            name=message.document.file_name,
            size=message.document.file_size
        )
        
        # Get user directory
        user_dir = create_user_dir(user_id)
        pdf_file.path = os.path.join(user_dir, f"pdf_{len(pdf_files_store[user_id]) + 1}.pdf")
        
        # Download file
        start_time = time.time()
        await message.download(
            pdf_file.path,
            progress=update_progress,
            progress_args=(
                message,
                user_id,
                "📥 **PDF ডাউনলোড করা হচ্ছে...**",
                start_time
            )
        )
        
        # Add to list
        pdf_files_store[user_id].append(pdf_file)
        
        # Update status
        if len(pdf_files_store[user_id]) < required_files_store[user_id]:
            status_text = await get_status_text(user_id)
            await edit_or_reply(message, user_id, status_text)
            return
            
        # If all files received, start merging
        await merge_pdfs(message, user_id)
        
    except asyncio.CancelledError:
        await cleanup(user_id)
        raise
    except Exception as e:
        await cleanup(user_id)
        await message.reply_text(f"❌ এরর: {str(e)}")

async def merge_pdfs(message: Message, user_id: int):
    """Merge PDF files."""
    try:
        # Update status
        await edit_or_reply(message, user_id, "🔄 **PDF ফাইলগুলি একত্রিত করা হচ্ছে...**")
        
        # Create output PDF
        output_path = os.path.join(create_user_dir(user_id), "merged.pdf")
        
        # Merge PDFs
        with pikepdf.Pdf.new() as output_pdf:
            for pdf_file in pdf_files_store[user_id]:
                with pikepdf.Pdf.open(pdf_file.path) as pdf:
                    output_pdf.pages.extend(pdf.pages)
            output_pdf.save(output_path)
        
        # Send merged file
        await edit_or_reply(message, user_id, "📤 **একত্রিত PDF ফাইল পাঠানো হচ্ছে...**")
        
        start_time = time.time()
        await message.reply_document(
            document=output_path,
            caption=(
                "✅ **PDF ফাইল একত্রিত করা হয়েছে!**\n\n"
                f"• মোট ফাইল: {len(pdf_files_store[user_id])}টি\n"
                f"• ফাইল লিস্ট:\n" + 
                "\n".join(f"{i+1}. {pdf.name}" for i, pdf in enumerate(pdf_files_store[user_id]))
            ),
            progress=update_progress,
            progress_args=(
                message,
                user_id,
                "📤 **একত্রিত PDF ফাইল পাঠানো হচ্ছে...**",
                start_time
            )
        )
        
    finally:
        await cleanup(user_id)

async def cleanup(user_id: int):
    """Clean up after process completion."""
    try:
        await end_process(user_id)
        cleanup_user_dir(user_id)
        await cleanup_status(user_id)
        
        # Clear PDF files store
        if user_id in pdf_files_store:
            del pdf_files_store[user_id]
        if user_id in required_files_store:
            del required_files_store[user_id]
            
    except Exception as e:
        print(f"Cleanup error: {str(e)}")
