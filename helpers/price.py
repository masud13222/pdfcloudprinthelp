from pyrogram import Client, filters
from pyrogram.types import Message
import math

def calculate_sheets(total_pages: int, layout: str) -> float:
    """Calculate number of sheets needed."""
    slides_per_sheet = {
        'L4': 8,   # 4 slides per side * 2 sides
        'L6': 12,  # 6 slides per side * 2 sides
        'L8': 16,  # 8 slides per side * 2 sides
        'P1': 2,   # 1 slide per side * 2 sides
        'P3': 6,   # 3 slides per side * 2 sides
        'P4': 8    # 4 slides per side * 2 sides
    }
    
    if layout not in slides_per_sheet:
        return 0
        
    return math.ceil(total_pages / slides_per_sheet[layout])

def calculate_price(sheets: int, price_per_sheet: float = 1.8) -> float:
    """Calculate total price."""
    return sheets * price_per_sheet

async def show_layout_guide(message: Message):
    """Show layout guide and calculation method."""
    await message.reply_text(
        "📖 **প্রিন্টিং লেআউট গাইড**\n\n"
        "**ℹ️ বিশেষ দ্রষ্টব্য:**\n"
        "• প্রতিটি শীটের দুই পৃষ্ঠায় প্রিন্ট হয়\n"
        "• যেমন: L4 = প্রতি পৃষ্ঠায় 4টি = প্রতি শীটে 8টি\n\n"
        "**🔄 ল্যান্ডস্কেপ মোড:**\n"
        "• L4 = প্রতি পৃষ্ঠায় 4টি স্লাইড (মোট 8টি)\n"
        "• L6 = প্রতি পৃষ্ঠায় 6টি স্লাইড (মোট 12টি)\n"
        "• L8 = প্রতি পৃষ্ঠায় 8টি স্লাইড (মোট 16টি)\n\n"
        "**📄 পোর্ট্রেট মোড:**\n"
        "• P1 = প্রতি পৃষ্ঠায় 1টি স্লাইড (মোট 2টি)\n"
        "• P3 = প্রতি পৃষ্ঠায় 3টি স্লাইড (মোট 6টি)\n"
        "• P4 = প্রতি পৃষ্ঠায় 4টি স্লাইড (মোট 8টি)\n\n"
        "**💰 হিসাব পদ্ধতি:**\n"
        "• প্রতি শীটের দাম = ১.৮০ টাকা\n"
        "• শীট সংখ্যা = ⌈মোট পেজ ÷ প্রতি শীটে স্লাইড সংখ্যা⌉\n"
        "• মোট দাম = শীট সংখ্যা × ১.৮০\n"
        "• কুরিয়ার চার্জ আলাদা (WhatsApp এ যোগাযোগ করুন)\n\n"
        "**📱 যোগাযোগ:**\n"
        "• [WhatsApp করুন](https://api.whatsapp.com/send?phone=8801880215950&text=PDF%20প্রিন্টিং%20সম্পর্কে%20জানতে%20চাই)\n\n"
        "**📝 কমান্ড ব্যবহার:**\n"
        "• একটি PDF: /price 23 -L4\n"
        "• একাধিক PDF: /price 23,45,67 -L4\n"
        "• শুধু গাইড দেখতে: /price",
        disable_web_page_preview=True
    )

async def price_command(client: Client, message: Message):
    """Handle /price command."""
    try:
        # Get command text
        cmd = message.text.strip()
        
        # If no arguments, show guide
        if cmd == "/price":
            await show_layout_guide(message)
            return
            
        # Parse command
        parts = cmd.split()
        if len(parts) != 3 or not parts[2].startswith('-'):
            await message.reply_text(
                "❌ **ভুল কমান্ড!**\n\n"
                "সঠিক ফরম্যাট:\n"
                "• একটি PDF: /price 23 -L4\n"
                "• একাধিক PDF: /price 23,45,67 -L4\n"
                "• গাইড দেখতে: /price"
            )
            return
            
        # Get pages and layout
        pages_str = parts[1]
        layout = parts[2][1:].upper()  # Remove - and convert to uppercase
        
        # Validate layout
        valid_layouts = ['L4', 'L6', 'L8', 'P1', 'P3', 'P4']
        if layout not in valid_layouts:
            await message.reply_text(
                "❌ **অবৈধ লেআউট!**\n\n"
                "সঠিক লেআউট:\n"
                "• ল্যান্ডস্কেপ: L4, L6, L8\n"
                "• পোর্ট্রেট: P1, P3, P4\n\n"
                "বিস্তারিত জানতে /price কমান্ড দিন।"
            )
            return
            
        # Parse page numbers
        try:
            pages = [int(p) for p in pages_str.split(',')]
        except:
            await message.reply_text(
                "❌ **অবৈধ পেজ সংখ্যা!**\n\n"
                "সঠিক ফরম্যাট:\n"
                "• একটি PDF: 23\n"
                "• একাধিক PDF: 23,45,67"
            )
            return
            
        # Calculate total pages
        total_pages = sum(pages)
        
        # Calculate sheets and price for each PDF
        individual_calcs = []
        total_sheets = 0
        total_price = 0
        
        for i, page in enumerate(pages, 1):
            sheets = calculate_sheets(page, layout)
            price = calculate_price(sheets)
            total_sheets += sheets
            total_price += price
            individual_calcs.append(
                f"{i}. পেজ সংখ্যা - {page}টি\n"
                f"   • শীট - {sheets}টি\n"
                f"   • দাম - {price:.1f} টাকা\n"
            )
        
        # Calculate combined total
        combined_sheets = calculate_sheets(total_pages, layout)
        combined_price = calculate_price(combined_sheets)
        
        # Show calculation
        await message.reply_text(
            "📊 **প্রিন্টিং হিসাব**\n\n"
            f"**📑 আলাদা হিসাব:**\n{''.join(individual_calcs)}\n"
            f"**📊 মোট (আলাদা):**\n"
            f"• মোট শীট: {total_sheets}টি\n"
            f"• মোট দাম: {total_price:.1f} টাকা\n\n"
            f"**📊 মোট (একসাথে):**\n"
            f"• মোট পেজ: {total_pages}টি\n"
            f"• মোট শীট: {combined_sheets}টি\n"
            f"• মোট দাম: {combined_price:.1f} টাকা\n\n"
            f"**🖨️ প্রিন্টিং তথ্য:**\n"
            f"• লেআউট: {layout}\n"
            f"• প্রতি শীটে স্লাইড: {8 if layout == 'L4' else 12 if layout == 'L6' else 16 if layout == 'L8' else 2 if layout == 'P1' else 6 if layout == 'P3' else 8}টি\n\n"
            "**📱 যোগাযোগ:**\n"
            "• [WhatsApp করুন](https://api.whatsapp.com/send?phone=8801880215950&text=PDF%20প্রিন্টিং%20সম্পর্কে%20জানতে%20চাই)\n\n"
            "**ℹ️ বিস্তারিত জানতে** /price **কমান্ড দিন।**",
            disable_web_page_preview=True
        )
            
    except Exception as e:
        await message.reply_text(
            "❌ **দুঃখিত! হিসাব করতে সমস্যা হয়েছে।**\n\n"
            f"কারণ: {str(e)}\n"
            "অনুগ্রহ করে আবার চেষ্টা করুন।"
        )
