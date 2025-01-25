from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from .users import is_admin

# Load environment variables
load_dotenv()

# MongoDB setup
mongo_client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
db = mongo_client[os.getenv('DB_NAME')]
settings_collection = db['group_settings']

async def get_settings_keyboard():
    """Get settings keyboard."""
    settings = await settings_collection.find_one({"_id": "bot_settings"}) or {}
    
    buttons = [
        [InlineKeyboardButton(
            f"🔗 লিংক ফিল্টার {'✅ চালু' if settings.get('link_filter') else '❌ বন্ধ'}",
            callback_data="link_filter"
        )],
        [InlineKeyboardButton(
            f"👋 ওয়েলকাম মেসেজ {'✅ চালু' if settings.get('welcome_msg') else '❌ বন্ধ'}", 
            callback_data="welcome_msg"
        )],
        [InlineKeyboardButton(
            "✏️ ওয়েলকাম মেসেজ সেট করুন",
            callback_data="set_welcome"
        )],
        [InlineKeyboardButton(
            f"⏰ ওয়েলকাম টাইম: {settings.get('welcome_time', '60')} সেকেন্ড",
            callback_data="welcome_time"
        )],
        [InlineKeyboardButton(
            f"👥 সার্ভিস মেসেজ {'✅ অটো ডিলিট' if settings.get('service_delete') else '❌ ডিলিট বন্ধ'}", 
            callback_data="service_delete"
        )],
        [InlineKeyboardButton(
            "📝 WhatsApp কীওয়ার্ড",
            callback_data="set_whatsapp"
        )],
        [InlineKeyboardButton(
            "📞 নাম্বার কীওয়ার্ড",
            callback_data="set_number"
        )],
        [InlineKeyboardButton(
            "✉️ টেক্সট কীওয়ার্ড",
            callback_data="set_text"
        )],
        [InlineKeyboardButton("🔄 সব রিসেট করুন", callback_data="reset_all")],
        [InlineKeyboardButton("❌ বন্ধ করুন", callback_data="close")]
    ]
    
    return InlineKeyboardMarkup(buttons)

async def get_settings_status():
    """Get current settings status."""
    settings = await settings_collection.find_one({"_id": "bot_settings"}) or {}
    
    status = (
        "**🔰 বর্তমান সেটিংস:**\n\n"
        f"• **লট স্ট্যাটাস:** {'✅ চালু আছে' if settings.get('is_active') else '❌ বন্ধ আছে'}\n"
        f"• **লিংক ফিল্টার:** {'✅ চালু' if settings.get('link_filter') else '❌ বন্ধ'}\n"
        f"• **ওয়েলকাম মেসেজ:** {'✅ চালু' if settings.get('welcome_msg') else '❌ বন্ধ'}\n"
        f"• **ওয়েলকাম টেক্সট:** {settings.get('welcome_text', 'সেট করা হয়নি')}\n"
        f"• **ওয়েলকাম টাইম:** {settings.get('welcome_time', '60')} সেকেন্ড\n"
        f"• **সার্ভিস মেসেজ:** {'✅ অটো ডিলিট' if settings.get('service_delete') else '❌ ডিলিট বন্ধ'}\n\n"
        f"**📝 কীওয়ার্ড টেমপ্লেট:**\n"
        f"• **WhatsApp:** {settings.get('whatsapp_template', 'সেট করা হয়নি')}\n"
        f"• **নাম্বার:** {settings.get('number_template', 'সেট করা হয়নি')}\n"
        f"• **টেক্সট:** {settings.get('text_template', 'সেট করা হয়নি')}"
    )
    
    return status

async def get_username_keyboard():
    """Get username setting keyboard."""
    buttons = [
        [InlineKeyboardButton("🔄 রিসেট", callback_data="reset_username")],
        [InlineKeyboardButton("🔙 ফিরে যান", callback_data="back")]
    ]
    return InlineKeyboardMarkup(buttons)

async def uset_command(client: Client, message: Message):
    """Handle /uset command."""
    try:
        # Check if user is admin
        if not await is_admin(message.from_user.id):
            await message.reply_text(
                "❌ **অননুমোদিত অ্যাক্সেস!**\n\n"
                "শুধুমাত্র অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।"
            )
            return
            
        # Show settings with status
        await message.reply_text(
            "⚙️ **বট সেটিংস**\n\n" +
            await get_settings_status() + "\n\n"
            "নিচের বাটনগুলি ব্যবহার করে সেটিংস পরিবর্তন করুন:",
            reply_markup=await get_settings_keyboard()
        )
            
    except Exception as e:
        await message.reply_text(f"❌ **এরর!**\n\n{str(e)}")

async def settings_callback(client: Client, callback: CallbackQuery):
    """Handle settings callbacks."""
    try:
        # Check if user is admin
        if not await is_admin(callback.from_user.id):
            await callback.answer(
                "শুধুমাত্র অ্যাডমিন এই সেটিংস পরিবর্তন করতে পারবেন।",
                show_alert=True
            )
            return
            
        # Handle reset all
        if callback.data == "reset_all":
            await settings_collection.update_one(
                {"_id": "bot_settings"},
                {"$unset": {
                    "whatsapp_template": "",
                    "number_template": "",
                    "text_template": "",
                    "welcome_text": "",
                    "welcome_time": "",
                    "welcome_msg": "",
                    "service_delete": "",
                    "link_filter": ""
                }},
                upsert=True
            )
            await callback.answer("সব সেটিংস রিসেট করা হয়েছে!", show_alert=True)

        # Handle set welcome message
        elif callback.data == "set_welcome":
            await callback.message.edit_text(
                "✏️ **ওয়েলকাম মেসেজ সেট করুন**\n\n"
                "নতুন ওয়েলকাম মেসেজ টেক্সট পাঠান।\n\n"
                "**উপলব্ধ ভ্যারিয়েবল:**\n"
                "• {mention} - মেম্বারের মেনশন\n"
                "• {title} - গ্রুপের নাম\n"
                "• {count} - মোট মেম্বার\n"
                "• {first} - মেম্বারের নাম\n"
                "• {last} - মেম্বারের শেষ নাম\n"
                "• {username} - মেম্বারের ইউজারনেম\n\n"
                "**উদাহরণ:**\n"
                "স্বাগতম {mention}!\n"
                "{title} গ্রুপে আপনাকে স্বাগতম।\n"
                "আমাদের মোট সদস্য {count} জন।\n\n"
                "বাতিল করতে /cancel টাইপ করুন।",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ফিরে যান", callback_data="back")]
                ])
            )
            
            # Set user state
            await settings_collection.update_one(
                {"_id": f"state_{callback.from_user.id}"},
                {"$set": {"waiting_for": "welcome_text"}},
                upsert=True
            )
            return

        # Handle set whatsapp template
        elif callback.data == "set_whatsapp":
            await callback.message.edit_text(
                "📝 **WhatsApp টেমপ্লেট সেট করুন**\n\n"
                "দিচের ফরম্যাটে লিখুন:\n"
                "`কীওয়ার্ড১,কীওয়ার্ড২ | নাম্বার`\n\n"
                "উদাহরণ:\n"
                "`whatsapp,wp,واتس | 8801234567890`\n\n"
                "• কমা দিয়ে একাধিক কীওয়ার্ড দিতে পারবেন\n"
                "• | চিহ্নের পর শুধু নাম্বার দিবেন\n"
                "• বট নিজেই কুন্দর বাটন তৈরি করবে\n\n"
                "বাতিল করতে /cancel টাইপ করুন।",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ফিরে যান", callback_data="back")]
                ])
            )
            
            # Set user state
            await settings_collection.update_one(
                {"_id": f"state_{callback.from_user.id}"},
                {"$set": {"waiting_for": "whatsapp_template"}},
                upsert=True
            )
            return

        # Handle set number template
        elif callback.data == "set_number":
            await callback.message.edit_text(
                "📞 **নল নাম্বার সেট করুন**\n\n"
                "নিচের ফরম্যাটে লিখুন:\n"
                "`কীওয়ার্ড১,কীওয়ার্ড২ | নাম্বার`\n\n"
                "উদাহরণ:\n"
                "`number,phone,নাম্বার,ফোন | 01234567890`\n\n"
                "• কমা দিয়ে একাধিক কীওয়ার্ড দিতে পারবেন\n"
                "• | চিহ্নের পর শুধু নাম্বার দিবেন\n"
                "• বট নিজেই কল বাটন তৈরি করবে\n\n"
                "বাতিল করতে /cancel টাইপ করুন।",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ফিরে যান", callback_data="back")]
                ])
            )
            
            # Set user state
            await settings_collection.update_one(
                {"_id": f"state_{callback.from_user.id}"},
                {"$set": {"waiting_for": "number_template"}},
                upsert=True
            )
            return

        # Handle set text template
        elif callback.data == "set_text":
            await callback.message.edit_text(
                "✉️ **টেক্সট টেমপ্লেট সেট করুন**\n\n"
                "দযচের ফরম্যাটে টেমপ্লেট পাঠান:\n"
                "`কীওয়ার্ড১,কীওয়ার্ড২ | টেমপ্লেট/লিংক`\n\n"
                "উদাহরণ:\n"
                "`text,message,মেসেজ | আমাদের টেলিগ্রাম গ্রুপে যোগ দিন: @groupname`\n\n"
                "বাতিল করতে /cancel টাইপ করুন।",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ফিরে যান", callback_data="back")]
                ])
            )
            
            # Set user state
            await settings_collection.update_one(
                {"_id": f"state_{callback.from_user.id}"},
                {"$set": {"waiting_for": "text_template"}},
                upsert=True
            )
            return
            
        # Handle back button
        elif callback.data == "back":
            # Clear user state
            await settings_collection.delete_one({"_id": f"state_{callback.from_user.id}"})
            
        # Handle link filter toggle
        elif callback.data == "link_filter":
            settings = await settings_collection.find_one({"_id": "bot_settings"}) or {}
            current = not settings.get("link_filter", False)
            await settings_collection.update_one(
                {"_id": "bot_settings"},
                {"$set": {"link_filter": current}},
                upsert=True
            )
            
        # Handle welcome message toggle
        elif callback.data == "welcome_msg":
            settings = await settings_collection.find_one({"_id": "bot_settings"}) or {}
            current = not settings.get("welcome_msg", False)
            await settings_collection.update_one(
                {"_id": "bot_settings"},
                {"$set": {"welcome_msg": current}},
                upsert=True
            )
            
        # Handle welcome time
        elif callback.data == "welcome_time":
            settings = await settings_collection.find_one({"_id": "bot_settings"}) or {}
            current = int(settings.get("welcome_time", 60))
            
            # Cycle through options: 30, 60, 120, 300 seconds
            if current == 30:
                new_time = 60
            elif current == 60:
                new_time = 120  
            elif current == 120:
                new_time = 300
            else:
                new_time = 30
                
            await settings_collection.update_one(
                {"_id": "bot_settings"},
                {"$set": {"welcome_time": new_time}},
                upsert=True
            )
            
        # Handle service message delete toggle
        elif callback.data == "service_delete":
            settings = await settings_collection.find_one({"_id": "bot_settings"}) or {}
            current = not settings.get("service_delete", False)
            await settings_collection.update_one(
                {"_id": "bot_settings"},
                {"$set": {"service_delete": current}},
                upsert=True
            )
            
        # Handle close button
        elif callback.data == "close":
            await callback.message.delete()
            return

        # Update message with new settings
        text = "⚙️ **বট সেটিংস**\n\n" + await get_settings_status() + "\n\n" + "নিচের বাটনগুলি ব্যবহার করে সেটিংস পরিবর্তন করুন:"
        markup = await get_settings_keyboard()
        
        try:
            if text != callback.message.text or markup != callback.message.reply_markup:
                await callback.message.edit_text(text, reply_markup=markup)
            else:
                await callback.answer()
        except Exception as e:
            print(f"Error updating message: {str(e)}")
            await callback.answer()
            
    except Exception as e:
        await callback.answer(f"এরর: {str(e)}", show_alert=True)

# Message handler for welcome text
@Client.on_message(filters.private & ~filters.command("cancel"))
async def handle_welcome_text(client: Client, message: Message):
    """Handle welcome text input."""
    try:
        # Check if waiting for welcome text
        state = await settings_collection.find_one({"_id": f"state_{message.from_user.id}"})
        if not state:
            return
            
        waiting_for = state.get("waiting_for")
        if not waiting_for:
            return
            
        if waiting_for == "welcome_text":
            # Save welcome text
            await settings_collection.update_one(
                {"_id": "bot_settings"},
                {"$set": {"welcome_text": message.text}},
                upsert=True
            )
        elif waiting_for == "whatsapp_template":
            # Save whatsapp template
            await settings_collection.update_one(
                {"_id": "bot_settings"},
                {"$set": {"whatsapp_template": message.text}},
                upsert=True
            )
        elif waiting_for == "number_template":
            # Save number template
            await settings_collection.update_one(
                {"_id": "bot_settings"},
                {"$set": {"number_template": message.text}},
                upsert=True
            )
        elif waiting_for == "text_template":
            # Save text template
            await settings_collection.update_one(
                {"_id": "bot_settings"},
                {"$set": {"text_template": message.text}},
                upsert=True
            )
        else:
            return
            
        # Clear user state
        await settings_collection.delete_one({"_id": f"state_{message.from_user.id}"})
        
        # Show success message
        text = "✅ **সেটিংস আপডেট করা হয়েছে!**\n\n" + await get_settings_status()
        markup = await get_settings_keyboard()
        
        try:
            await message.reply_text(text, reply_markup=markup)
        except Exception as e:
            print(f"Error sending success message: {str(e)}")
            await message.reply_text("✅ সেটিংস আপডেট করা হয়েছে!")
            
    except Exception as e:
        await message.reply_text(f"❌ **এরর!**\n\n{str(e)}")

# Add new message handler for username
@Client.on_message(filters.private & ~filters.command("cancel"))
async def handle_username_text(client: Client, message: Message):
    """Handle username text input."""
    try:
        # Check if waiting for username
        state = await settings_collection.find_one({"_id": f"state_{message.from_user.id}"})
        if not state or state.get("waiting_for") != "group_username":
            return
            
        # Remove @ if present
        username = message.text.replace("@", "").strip()
        
        # Save username
        await settings_collection.update_one(
            {"_id": "bot_settings"},
            {"$set": {"group_username": username}},
            upsert=True
        )
        
        # Clear user state
        await settings_collection.delete_one({"_id": f"state_{message.from_user.id}"})
        
        # Show success message
        await message.reply_text(
            "✅ **গ্রুপ ইউজারনেম সেট করা হয়েছে!**",
            reply_markup=await get_settings_keyboard()
        )
            
    except Exception as e:
        await message.reply_text(f"❌ **এরর!**\n\n{str(e)}")

async def groupon_command(client: Client, message: Message):
    """Handle /groupon command."""
    try:
        # Check if user is admin
        if not await is_admin(message.from_user.id):
            await message.reply_text(
                "❌ **অননুমোদিত অ্যাক্সেস!**\n\n"
                "শুধুমাত্র অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।"
            )
            return

        # Check if bot is admin in group
        chat_member = await message.chat.get_member("me")
        if not chat_member.privileges.can_delete_messages:
            await message.reply_text(
                "❌ **বট অ্যাডমিন নয়!**\n\n"
                "দয়া করে বটকে অ্যাডমিন করুন এবং নিচের পারমিশনগুলি দিন:\n"
                "• Delete messages\n"
                "• Ban users\n"
                "• Add new admins\n"
                "• Manage group"
            )
            return

        # Activate bot
        await settings_collection.update_one(
            {"_id": "bot_settings"},
            {"$set": {"is_active": True}},
            upsert=True
        )
        
        await message.reply_text(
            "✅ **বট সক্রিয় করা হয়েছে!**\n\n"
            "এখন থেকে বট গ্রুপে কাজ করা শুরু করবে।\n"
            "• ওয়েলকাম মেসেজ দেখাবে\n"
            "• সার্ভিস মেসেজ ডিলিট করবে\n"
            "• লিংক ফিল্টার কাজ করবে"
        )
            
    except Exception as e:
        await message.reply_text(f"❌ **এরর!**\n\n{str(e)}")

async def groupoff_command(client: Client, message: Message):
    """Handle /groupoff command."""
    try:
        # Check if user is admin
        if not await is_admin(message.from_user.id):
            await message.reply_text(
                "❌ **অননুমোদিত অ্যাক্সেস!**\n\n"
                "শুধুমাত্র অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।"
            )
            return

        # Deactivate bot
        await settings_collection.update_one(
            {"_id": "bot_settings"},
            {"$set": {"is_active": False}},
            upsert=True
        )
        
        await message.reply_text(
            "❌ **বট নিষ্ক্রিয় করা হয়েছে!**\n\n"
            "এখন থেকে বট গ্রুপে কোন কাজ করবে না।\n"
            "আবার চালু করতে /groupon কমান্ড দিন।"
        )
            
    except Exception as e:
        await message.reply_text(f"❌ **এরর!**\n\n{str(e)}")

# Add new function to check if bot is active
async def is_bot_active():
    """Check if bot is active in group."""
    settings = await settings_collection.find_one({"_id": "bot_settings"}) or {}
    return settings.get('is_active', False)
