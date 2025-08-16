import telebot
from telebot import types
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
CHANNEL_TITLE = os.getenv('CHANNEL_TITLE', "عيادات الحروف")
CHANNEL_LINK = os.getenv('CHANNEL_LINK', 'https://t.me/+W0lpVpFhNLxjNTM0')

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

def check_bot_permissions():
    """Verify bot has admin permissions in channel"""
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, bot.get_me().id)
        if chat_member.status not in ['administrator', 'creator']:
            logging.error("Bot is not admin in the channel!")
            return False
        
        permissions = chat_member.get('permissions', {})
        required_perms = ['can_send_messages', 'can_send_media_messages']
        
        if not all(permissions.get(perm, False) for perm in required_perms):
            logging.error("Bot lacks required permissions!")
            return False
            
        logging.info(f"Bot has {chat_member.status} permissions in {CHANNEL_TITLE}")
        return True
        
    except Exception as e:
        logging.error(f"Permission check failed: {str(e)}")
        return False

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Enhanced welcome message with channel info"""
    welcome_msg = f"""
    السلام عليكم ورحمة الله وبركاته 🌸

    أهلاً بكِ في بوت {CHANNEL_TITLE} لحفظ القرآن الكريم.

    📌 كيفية الإرسال:
    1. اضغط على أيقونة الميكروفون
    2. سجلي الوجه المطلوب
    3. اكتبي اسمك في وصف الرسالة

    التسجيلات ترسل إلى: [قناة {CHANNEL_TITLE}]({CHANNEL_LINK})
    
    للتأكد من حالة البوت: /status
    """
    try:
        bot.reply_to(message, welcome_msg, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error sending welcome: {str(e)}")

@bot.message_handler(commands=['status'])
def bot_status(message):
    """Check bot status"""
    status_msg = "✅ البوت يعمل بشكل طبيعي\n"
    status_msg += f"📊 القناة المستهدفة: {CHANNEL_TITLE}\n"
    status_msg += f"🆔 معرف القناة: {CHANNEL_ID}"
    
    bot.reply_to(message, status_msg)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    """Process voice messages with enhanced error handling"""
    if not check_bot_permissions():
        try:
            bot.reply_to(
                message,
                "⚠️ البوت لا يملك الصلاحيات الكافية في القناة",
                reply_markup=types.InlineKeyboardMarkup().row(
                    types.InlineKeyboardButton(
                        "إضافة البوت إلى القناة",
                        url=f"https://t.me/{bot.get_me().username}?startchannel=true"
                    )
                )
            )
        except Exception as e:
            logging.error(f"Permission error reply failed: {str(e)}")
        return

    try:
        user = message.from_user
        caption = (
            f"تسجيل جديد من: {user.first_name or 'مستخدم'}\n"
            f"المعرف: @{user.username or 'غير متوفر'}\n"
            f"الرقم: {user.id}"
        )

        # Send to channel
        msg = bot.send_voice(
            chat_id=CHANNEL_ID,
            voice=message.voice.file_id,
            caption=caption,
            parse_mode="Markdown"
        )

        # User confirmation
        bot.reply_to(
            message,
            "✅ تم استلام تسجيلكِ بنجاح وسيتم المراجعة قريباً",
            reply_to_message_id=message.message_id
        )
        
        logging.info(f"Voice forwarded to {CHANNEL_ID}, message ID: {msg.message_id}")

    except Exception as e:
        error_msg = "❌ تعذر إرسال التسجيل. يرجى المحاولة لاحقاً"
        if "Forbidden" in str(e):
            error_msg = "🔒 البوت محظور من القناة!"
        elif "Bad Request" in str(e):
            error_msg = "📛 المعرف غير صحيح أو القناة غير موجودة"
            
        bot.reply_to(message, error_msg)
        logging.error(f"Voice processing error: {str(e)}")

@bot.message_handler(func=lambda m: True)
def handle_other_messages(message):
    """Handle all other messages"""
    if message.content_type == 'text':
        bot.reply_to(
            message,
            "📢 يرجى إرسال تسجيل صوتي فقط\n"
            "استخدمي /start لمعرفة التعليمات"
        )

if __name__ == '__main__':
    try:
        # Initial checks
        logging.info(f"Starting bot for channel: {CHANNEL_TITLE} (ID: {CHANNEL_ID})")
        
        if not all([TOKEN, CHANNEL_ID]):
            logging.critical("Missing required environment variables!")
            exit(1)
            
        if check_bot_permissions():
            bot.delete_webhook()
            logging.info("Starting polling...")
            bot.polling(none_stop=True, interval=2, timeout=60)
        else:
            logging.critical("Insufficient permissions! Shutting down.")
            
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}")