from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from dotenv import load_dotenv
import os
import asyncio
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from helpers.merge import merge_command, handle_pdf
from group.users import users_command
from group.broadcast import broadcast_command
from group.database import (
    start_command,
    handle_force_sub_callback,
    check_subscription,
    force_sub_message
)
from helpers.cancel import cancel_command
from helpers.invert import invert_command
from helpers.inverts import inverts_command
from helpers.drive import drive_command
from helpers.price import price_command
from helpers.pages import pages_command
from helpers.invertnew import invertnew_command
from group.settings import (
    uset_command, 
    settings_callback,
    handle_welcome_text,
    handle_username_text,
    groupon_command,
    groupoff_command,
    is_bot_active,
    settings_collection
)

# Simple HTTP Server for health checks
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_health_server():
    port = int(os.getenv('PORT', 8080))
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    print(f"Starting health check server on port {port}")
    httpd.serve_forever()

# Start health check server in a separate thread
threading.Thread(target=run_health_server, daemon=True).start()

# Load environment variables
load_dotenv()

# Initialize bot
bot = Client(
    "pdf_merger_bot",
    api_id=os.getenv('API_ID'),
    api_hash=os.getenv('API_HASH'),
    bot_token=os.getenv('BOT_TOKEN')
)

# Register command handlers
@bot.on_message(filters.command("merge") & filters.private)
async def merge_handler(client, message):
    if not await force_sub_check(client, message):
        return
    await merge_command(client, message)

@bot.on_message(filters.command("allcancel") & filters.private)
async def allcancel_handler(client, message):
    if not await force_sub_check(client, message):
        return
    await cancel_command(client, message)

@bot.on_message(filters.command("invert") & filters.private)
async def invert_handler(client, message):
    if not await force_sub_check(client, message):
        return
    await invert_command(client, message)

@bot.on_message(filters.command("inverts") & filters.private)
async def inverts_handler(client, message):
    if not await force_sub_check(client, message):
        return
    await inverts_command(client, message)

@bot.on_message(filters.command("invertnew") & filters.private)
async def invertnew_handler(client, message):
    print("Invertnew command received")
    if not await force_sub_check(client, message):
        return
    await invertnew_command(client, message)

@bot.on_message(filters.command("users") & filters.private)
async def users_handler(client, message):
    if not await force_sub_check(client, message):
        return
    await users_command(client, message)

@bot.on_message(filters.command("pdf") & filters.private)
async def pdf_handler(client, message):
    if not await force_sub_check(client, message):
        return
    await drive_command(client, message)

# Register PDF file handler
@bot.on_message(filters.document & filters.private)
async def pdf_handler(client, message):
    if not await force_sub_check(client, message):
        return
    await handle_pdf(client, message)

# Price calculation command
@bot.on_message(filters.command("price") & filters.private)
async def price_handler(client, message):
    if not await force_sub_check(client, message):
        return
    await price_command(client, message)

# Add pages command handler
@bot.on_message(filters.command("pages") & filters.private)
async def pages_handler(client, message):
    if not await force_sub_check(client, message):
        return
    await pages_command(client, message)

@bot.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client, message):
    if not await force_sub_check(client, message):
        return
    await broadcast_command(client, message)

@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    await start_command(client, message)

@bot.on_message(filters.command("uset"))
async def uset_handler(client, message):
    if not await force_sub_check(client, message):
        return
    await uset_command(client, message)

@bot.on_callback_query()
async def callback_handler(client, callback_query):
    if callback_query.data == "checksub":
        await handle_force_sub_callback(client, callback_query)
    else:
        await settings_callback(client, callback_query)

# Add message handlers
@bot.on_message(filters.private & ~filters.command("cancel"))
async def message_handler(client, message):
    if not await force_sub_check(client, message):
        return
    await handle_welcome_text(client, message)
    await handle_username_text(client, message)

@bot.on_message(filters.command("groupon"))
async def groupon_handler(client, message):
    await groupon_command(client, message)

@bot.on_message(filters.command("groupoff"))
async def groupoff_handler(client, message):
    await groupoff_command(client, message)

# Add new handler for new chat members
@bot.on_message(filters.new_chat_members)
async def welcome_handler(client, message):
    try:
        # Check if bot is active
        if not await is_bot_active():
            return
            
        # Get settings
        settings = await settings_collection.find_one({"_id": "bot_settings"}) or {}
        
        # Delete service message if enabled
        if settings.get('service_delete'):
            await message.delete()
        
        # Check if welcome message is enabled
        if not settings.get('welcome_msg'):
            return
            
        # Get welcome text
        welcome_text = settings.get('welcome_text')
        if not welcome_text:
            return
            
        # Send welcome message
        for new_member in message.new_chat_members:
            if new_member.is_self:  # Skip if bot joined
                continue
                
            # Format welcome text
            text = welcome_text.format(
                mention=new_member.mention,
                title=message.chat.title,
                count=message.chat.members_count,
                first=new_member.first_name,
                last=new_member.last_name or "",
                username=new_member.username or ""
            )
            
            # Send message
            msg = await message.reply_text(text)
            
            # Delete after welcome_time seconds
            if settings.get('welcome_time'):
                await asyncio.sleep(int(settings.get('welcome_time')))
                await msg.delete()
    except Exception as e:
        print(f"Error in welcome handler: {str(e)}")

# Add service message handler
@bot.on_message(filters.service & ~filters.new_chat_members | filters.left_chat_member | filters.pinned_message | filters.migrate_from_chat_id | filters.migrate_to_chat_id | filters.channel_chat_created | filters.supergroup_chat_created | filters.group_chat_created | filters.delete_chat_photo | filters.new_chat_photo | filters.new_chat_title)
async def service_handler(client, message):
    try:
        # Check if bot is active
        if not await is_bot_active():
            return
            
        # Get settings
        settings = await settings_collection.find_one({"_id": "bot_settings"}) or {}
        
        # Check if service message delete is enabled
        if settings.get('service_delete'):
            await message.delete()
    except Exception as e:
        print(f"Error in service handler: {str(e)}")

# Add link filter handler
@bot.on_message(filters.text & filters.group)
async def link_handler(client, message):
    try:
        # Check if bot is active
        if not await is_bot_active():
            return
            
        # Get settings
        settings = await settings_collection.find_one({"_id": "bot_settings"}) or {}
        
        # Check for keywords
        text = message.text.lower()
        
        # Check whatsapp template
        if settings.get('whatsapp_template'):
            keywords, number = settings.get('whatsapp_template').split('|', 1)
            keywords = [k.strip().lower() for k in keywords.split(',')]
            if any(keyword in text for keyword in keywords):
                # Create WhatsApp and Telegram buttons
                telegram_username = os.getenv('TELEGRAM_CONTACT', 'mehedihasan9994')
                buttons = [
                    [InlineKeyboardButton(
                        "📱 WhatsApp এ যোগাযোগ করুন",
                        url=f"https://api.whatsapp.com/send?phone={number.strip().replace('+', '')}&text=PDF"
                    )],
                    [InlineKeyboardButton(
                        "📱 Telegram এ যোগাযোগ করুন",
                        url=f"https://t.me/{telegram_username}"
                    )]
                ]
                await message.reply_text(
                    "**📞 WhatsApp/Telegram এ যোগাযোগ করুন**\n\n"
                    "নিচের বাটনে ক্লিক করে সরাসরি WhatsApp অথবা Telegram এ চলে যান।",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                return
        
        # Check number template
        if settings.get('number_template'):
            keywords, number = settings.get('number_template').split('|', 1)
            keywords = [k.strip().lower() for k in keywords.split(',')]
            if any(keyword in text for keyword in keywords):
                # Create call button
                buttons = [
                    [InlineKeyboardButton(
                        "📞 কল করুন",
                        url=f"tel:{number.strip().replace('+', '')}"
                    )]
                ]
                await message.reply_text(
                    "**📞 ফোন করুন**\n\n"
                    "নিচের বাটনে ক্লিক করে সরাসরি কল করুন।",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                return
        
        # Check text template
        if settings.get('text_template'):
            keywords, template = settings.get('text_template').split('|', 1)
            keywords = [k.strip().lower() for k in keywords.split(',')]
            if any(keyword in text for keyword in keywords):
                await message.reply_text(template.strip())
                return
        
        # Check if link filter is enabled
        if settings.get('link_filter'):
            # Check if user is admin
            chat_member = await message.chat.get_member(message.from_user.id)
            if chat_member.privileges and (chat_member.privileges.can_delete_messages or chat_member.privileges.can_manage_chat):
                return  # Allow admins to post links
            
            text = message.text.lower()
            
            # Check for entities
            if message.entities:
                for entity in message.entities:
                    if entity.type in ["url", "text_link", "mention", "phone_number"]:
                        await message.delete()
                        return
            
            # Check for raw URLs and mentions
            if any(word.startswith(('http://', 'https://', 'www.', 't.me/', '@', '+')) for word in text.split()) or \
               't.me' in text or \
               'telegram.me' in text or \
               '.com' in text or \
               '.org' in text or \
               '.net' in text or \
               '.me' in text or \
               'http' in text or \
               '@' in text:
                await message.delete()
                return
    except Exception as e:
        print(f"Error in link handler: {str(e)}")

async def force_sub_check(client, message):
    """Check force subscription for all commands."""
    if not await check_subscription(client, message.from_user.id):
        text, markup = await force_sub_message()
        await message.reply_text(text, reply_markup=markup)
        return False
    return True

# Start the bot
bot.run() 