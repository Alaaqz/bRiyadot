import os
import telebot
from telebot import types
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# قراءة المتغيرات من البيئة
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0").strip())
CHANNEL_TITLE = os.getenv("CHANNEL_TITLE", "عيادات الحروف")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/+W0lpVpFhNLxjNTM0")

# تأكيد وجود التوكن
if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN غير موجود في Environment Variables!")

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id == ADMIN_USER_ID

def check_bot_permissions() -> bool:
    """Verify bot has required channel permissions"""
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, bot.get_me().id)
        
        if chat_member.status not in ["administrator", "creator"]:
            logging.error("Bot is not admin in channel!")
            return False

        required_perms = {
            "can_post_messages": "Post Messages",
            "can_send_media_messages": "Send Media"
        }

        for perm, name in required_perms.items():
            if not getattr(chat_member, perm, False):
                logging.error(f"Missing permission: {name}")
                return False

        return True

    except Exception as e:
        logging.error(f"Permission check failed: {str(e)}")
        return False

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    """Send welcome message with instructions"""
    welcome_msg = f"""
    السلام عليكم ورحمة الله وبركاته 🌸

    أهلاً بكِ في بوت {CHANNEL_TITLE} لحفظ القرآن الكريم.

    📌 كيفية الإرسال:
    1. اضغط على أيقونة الميكروفون
    2. سجلي الوجه المطلوب
    3. اكتبي اسمك في وصف الرسالة

    التسجيلات ترسل إلى: [قناة {CHANNEL_TITLE}]({CHANNEL_LINK})
    """
    try:
        bot.reply_to(message, welcome_msg, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error sending welcome: {str(e)}")

@bot.message_handler(commands=["status"])
def bot_status(message):
    """Check bot status"""
    status_msg = f"""
    ✅ حالة البوت:
    - القناة: {CHANNEL_TITLE}
    - المعرف: {CHANNEL_ID}
    - الصلاحيات: {"✅ جاهز" if check_bot_permissions() else "❌ تحتاج إصلاح"}
    """
    bot.reply_to(message, status_msg.strip())

@bot.message_handler(commands=["perms"])
def check_perms(message):
    """Check bot permissions in channel"""
    if not is_admin(message.from_user.id):
        return

    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, bot.get_me().id)
        perms_info = [
            f"صلاحيات البوت في {CHANNEL_TITLE}:",
            f"- الحالة: {chat_member.status}",
            f"- إرسال رسائل: {'✅' if getattr(chat_member, 'can_post_messages', False) else '❌'}",
            f"- إرسال وسائط: {'✅' if getattr(chat_member, 'can_send_media_messages', False) else '❌'}"
        ]
        bot.reply_to(message, "\n".join(perms_info))
    except Exception as e:
        bot.reply_to(message, f"خطأ في التحقق: {str(e)}")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    """Process and forward voice messages"""
    if not check_bot_permissions():
        bot.reply_to(
            message,
            "⚠️ البوت لا يملك الصلاحيات الكافية",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton(
                    "إصلاح الصلاحيات",
                    url=f"https://t.me/{bot.get_me().username}?startchannel=true"
                )
            )
        )
        return

    try:
        user = message.from_user
        caption = (
            f"تسجيل جديد من: {user.first_name or 'مستخدم'}\n"
            f"المعرف: @{user.username or 'غير متوفر'}\n"
            f"الرقم: {user.id}"
        )

        msg = bot.send_voice(
            chat_id=CHANNEL_ID,
            voice=message.voice.file_id,
            caption=caption,
            parse_mode="Markdown"
        )

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
        bot.reply_to(message, error_msg)
        logging.error(f"Voice processing error: {str(e)}")

@bot.message_handler(func=lambda m: True)
def handle_other_messages(message):
    """Handle all other messages"""
    if message.content_type == "text":
        bot.reply_to(
            message,
            "📢 يرجى إرسال تسجيل صوتي فقط\n"
            "استخدمي /start لمعرفة التعليمات"
        )

if __name__ == "__main__":
    try:
        logging.info(f"Starting bot for {CHANNEL_TITLE} (ID: {CHANNEL_ID})")
        
        if not all([TOKEN, CHANNEL_ID]):
            logging.critical("Missing required environment variables!")
            exit(1)
            
        if check_bot_permissions():
            bot.delete_webhook()
            logging.info("Bot started successfully")
            bot.polling(none_stop=True, interval=2, timeout=60)
        else:
            logging.critical("Insufficient permissions! Shutting down.")
            
    except Exception as e:
        logging.critical(f"Bot failed: {str(e)}")
