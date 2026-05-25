import os
import logging
from dotenv import load_dotenv
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from extractor import extract_shift_plan
from generator import generate_wallpaper

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_TELEGRAM_IDS = [int(uid.strip()) for uid in os.getenv("ALLOWED_TELEGRAM_IDS", "").split(",") if uid.strip()]
TARGET_PERSON_NAME = os.getenv("TARGET_PERSON_NAME", "Max Mustermann")
WALLPAPER_WIDTH = int(os.getenv("WALLPAPER_WIDTH", 1170))
WALLPAPER_HEIGHT = int(os.getenv("WALLPAPER_HEIGHT", 2532))
FONT_PATH = os.getenv("FONT_PATH", "./fonts/SFCompact.ttf")

client = genai.Client(api_key=GEMINI_API_KEY)

def is_authorized(user_id: int) -> bool:
    return not ALLOWED_TELEGRAM_IDS or user_id in ALLOWED_TELEGRAM_IDS

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("You're not a registered user for this service.")
        return

    if update.message.document:
        doc = update.message.document
        mime_type = doc.mime_type
        file_id = doc.file_id
    elif update.message.photo:
        mime_type = "image/jpeg"
        file_id = update.message.photo[-1].file_id
    else:
        return

    status_msg = await update.message.reply_text("Verarbeite Schichtplan... ⏳")
    
    try:
        file = await context.bot.get_file(file_id)
        file_bytes = await file.download_as_bytearray()
        
        schedule = await extract_shift_plan(client, bytes(file_bytes), mime_type, TARGET_PERSON_NAME)
        wallpaper_buffer = generate_wallpaper(schedule, WALLPAPER_WIDTH, WALLPAPER_HEIGHT, FONT_PATH)
        
        await status_msg.delete()
        await update.message.reply_photo(
            photo=wallpaper_buffer,
            caption=f"Hier ist dein Wallpaper für die Woche {schedule.get('woche')} ✨"
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(f"Fehler: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("You're not a registered user for this service.")
        return
    await update.message.reply_text(f"Hallo! Sende mir einen Schichtplan für {TARGET_PERSON_NAME}.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex('^/start$'), start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_message))
    logger.info("Class-free Bot started...")
    app.run_polling()
