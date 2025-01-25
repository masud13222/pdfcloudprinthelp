from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
import asyncio
import os
from dotenv import load_dotenv
from .users import is_admin, users_collection

async def broadcast_command(client: Client, message: Message):
    """Handle /broadcast command to send message to all users."""
    try:
        # Check if user is admin
        if not await is_admin(message.from_user.id):
            await message.reply_text(
                "❌ **অননুমোদিত অ্যাক্সেস!**\n\n"
                "শুধুমাত্র অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।"
            )
            return
            
        # Get broadcast message
        if message.reply_to_message:
            broadcast_msg = message.reply_to_message
        else:
            # Get text after command
            if len(message.text.split(" ", 1)) < 2:
                await message.reply_text(
                    "❌ **ভুল ব্যবহার!**\n\n"
                    "**সঠিক ব্যবহার:**\n"
                    "• কোন মেসেজে রিপ্লাই দিয়ে /broadcast\n"
                    "• /broadcast মেসেজ টেক্সট"
                )
                return
            broadcast_msg = message
            
        # Send status message
        status_msg = await message.reply_text(
            "📤 **ব্রডকাস্ট শুরু হচ্ছে...**\n\n"
            "অনুগ্রহ করে অপেক্ষা করুন।"
        )
        
        # Get all users
        all_users = users_collection.find({}, {"user_id": 1})
        
        # Initialize counters
        total_users = await users_collection.count_documents({})
        done = 0
        success = 0
        failed = 0
        blocked = 0
        deleted = 0
        
        async for user in all_users:
            done += 1
            try:
                if message.reply_to_message:
                    # Forward replied message
                    await broadcast_msg.forward(
                        chat_id=user["user_id"]
                    )
                else:
                    # Send text message
                    await client.send_message(
                        chat_id=user["user_id"],
                        text=broadcast_msg.text.split(" ", 1)[1]
                    )
                success += 1
                
            except FloodWait as e:
                await asyncio.sleep(e.value)
                # Retry after flood wait
                try:
                    if message.reply_to_message:
                        await broadcast_msg.forward(
                            chat_id=user["user_id"]
                        )
                    else:
                        await client.send_message(
                            chat_id=user["user_id"],
                            text=broadcast_msg.text.split(" ", 1)[1]
                        )
                    success += 1
                except:
                    failed += 1
                    
            except UserIsBlocked:
                blocked += 1
                failed += 1
                # Remove blocked user
                await users_collection.delete_one({"user_id": user["user_id"]})
                
            except InputUserDeactivated:
                deleted += 1
                failed += 1
                # Remove deleted user
                await users_collection.delete_one({"user_id": user["user_id"]})
                
            except PeerIdInvalid:
                failed += 1
                # Remove invalid user
                await users_collection.delete_one({"user_id": user["user_id"]})
                
            except Exception:
                failed += 1
                
            # Update status every 25 users
            if done % 25 == 0:
                try:
                    await status_msg.edit_text(
                        f"📤 **ব্রডকাস্ট চলছে...**\n\n"
                        f"• মোট ইউজার: {total_users:,}জন\n"
                        f"• সম্পন্ন: {done:,}জন\n"
                        f"• সফল: {success:,}জন\n"
                        f"• ব্যর্থ: {failed:,}জন\n"
                        f"• ব্লক করেছে: {blocked:,}জন\n"
                        f"• একাউন্ট ডিলিট: {deleted:,}জন\n\n"
                        f"**📊 অগ্রগতি:** {done/total_users:.1%}"
                    )
                except:
                    pass
                    
            # Sleep to avoid flood
            await asyncio.sleep(0.1)
                
        # Send completion message
        await status_msg.edit_text(
            f"✅ **ব্রডকাস্ট সম্পন্ন!**\n\n"
            f"• মোট ইউজার: {total_users:,}জন\n"
            f"• সফল: {success:,}জন\n"
            f"• ব্যর্থ: {failed:,}জন\n"
            f"• ব্লক করেছে: {blocked:,}জন\n"
            f"• একাউন্ট ডিলিট: {deleted:,}জন\n\n"
            f"সময় লেগেছে: {int((done/total_users)*100)}%"
        )
            
    except Exception as e:
        await message.reply_text(
            "❌ **এরর!**\n\n"
            f"কারণ: {str(e)}\n"
            "দয়া করে আবার চেষ্টা করুন।"
        ) 