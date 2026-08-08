import os
import sys
import random
import string
import requests
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8953592093:AAFNEScJPz_GR7jEaTsQY_u95A1AJK5ro_E")

FLASK_API_BASE_URL = os.getenv("FLASK_API_URL", "https://ff-follower-bot.onrender.com")
FLASK_API_URL = f"{FLASK_API_BASE_URL}/api/v1/generate-pass"

DEFAULT_EXPIRE_HOURS = 2

# Default channels if Flask cannot be reached or does not specify channels
REQUIRED_CHANNELS = [
    "@freefireob51",
    "@free_like_bot1",
    "@tom_codex1"
]

CHANNEL_LINKS = [
    "https://t.me/freefireob51",
    "https://t.me/free_like_bot1",
    "https://t.me/tom_codex1"
]
# =======================================================

def get_channels_config():
    """Dynamically fetch channels, links, and validity duration from Flask configuration"""
    try:
        response = requests.get(f"{FLASK_API_BASE_URL}/api/v1/config", timeout=4)
        if response.status_code == 200:
            config = response.json()
            c1 = config.get("channel_1")
            c2 = config.get("channel_2")
            c3 = config.get("channel_3")
            
            req_channels = []
            links = []
            
            for ch in [c1, c2, c3]:
                if ch:
                    handle = ch.strip()
                    if handle.startswith("https://t.me/"):
                        handle = "@" + handle.split("/")[-1]
                    elif not handle.startswith("@"):
                        handle = "@" + handle
                    
                    link = ch.strip()
                    if not link.startswith("http"):
                        link = f"https://t.me/{link.replace('@', '')}"
                    
                    req_channels.append(handle)
                    links.append(link)
            
            expire_hours = config.get("verification_expire_hours")
            if expire_hours is None:
                expire_hours = DEFAULT_EXPIRE_HOURS
            else:
                expire_hours = int(expire_hours)
                
            if len(req_channels) == 3:
                return req_channels, links, expire_hours
            else:
                return REQUIRED_CHANNELS, CHANNEL_LINKS, expire_hours
    except Exception as e:
        logger.error(f"Error loading dynamic configuration from Flask: {e}")
    return REQUIRED_CHANNELS, CHANNEL_LINKS, DEFAULT_EXPIRE_HOURS

def generate_random_password():
    """Generate a random dynamic Password/Token (e.g., 'FB-XXXXXX')"""
    digits = ''.join(random.choices(string.digits, k=6))
    return f"FB-{digits}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    user = update.effective_user
    req_channels, links, _ = get_channels_config()
    
    keyboard = []
    for idx, link in enumerate(links, 1):
        keyboard.append([InlineKeyboardButton(f"📢 Join Channel {idx}", url=link)])
    
    keyboard.append([InlineKeyboardButton("✅ VERIFY & GET PASSWORD", callback_data="verify_membership")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg_text = (
        f"👋 Welcome **{user.first_name}**!\n\n"
        "To unlock the **DEVELOPER YASIN** application, you must join all 3 official Telegram channels below.\n\n"
        "👉 Click each button to join, then tap **VERIFY & GET PASSWORD** to get your unique Passcode."
    )
    
    if update.message:
        await update.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode='Markdown')

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler to check membership and issue passcode"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    bot = context.bot
    
    req_channels, links, expire_hours = get_channels_config()
    is_all_joined = True

    # Check subscriber status on each channel
    for channel in req_channels:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                is_all_joined = False
                break
        except Exception as e:
            logger.error(f"Error checking status for {channel}: {e}")
            is_all_joined = False
            break

    # 1. Verification successful
    if is_all_joined:
        pass_code = generate_random_password()
        expire_time = datetime.now() + timedelta(hours=expire_hours)
        
        # Register on Flask Backend
        payload = {
            "telegram_id": str(user_id),
            "password": pass_code,
            "expire_hours": expire_hours
        }

        try:
            requests.post(FLASK_API_URL, json=payload, timeout=5)
        except Exception as e:
            logger.error(f"Flask API Connection error: {e}")

        success_text = (
            "🎉 **Verification Successful!** 🎉\n\n"
            "You have joined all required channels.\n\n"
            "🔑 **Your Password:**\n"
            f"`{pass_code}`\n\n"
            f"⏰ **Validity:** {expire_hours} Hours (Expires at: {expire_time.strftime('%I:%M %p')})\n\n"
            "👉 Tap on the password to copy, open the app, and paste it to unlock!"
        )
        await query.edit_message_text(text=success_text, parse_mode='Markdown')

    # 2. Verification failed
    else:
        warning_text = (
            "❌ **Verification Failed!**\n\n"
            "You have NOT joined all 3 channels yet.\n"
            "Please join all channels below and tap **TRY VERIFY AGAIN**."
        )
        
        keyboard = []
        for idx, link in enumerate(links, 1):
            keyboard.append([InlineKeyboardButton(f"📢 Join Channel {idx}", url=link)])
        keyboard.append([InlineKeyboardButton("🔄 TRY VERIFY AGAIN", callback_data="verify_membership")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=warning_text, reply_markup=reply_markup, parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_membership, pattern="^verify_membership$"))
    
    print("🤖 Telegram Verification Bot is running...")
    app.run_polling()
