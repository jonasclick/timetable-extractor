import os
import io
import logging
from typing import List
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants from .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TARGET_PERSON_NAME = os.getenv("TARGET_PERSON_NAME", "Max Mustermann")
WALLPAPER_WIDTH = int(os.getenv("WALLPAPER_WIDTH", 1170))
WALLPAPER_HEIGHT = int(os.getenv("WALLPAPER_HEIGHT", 2532))
FONT_PATH = os.getenv("FONT_PATH", "./fonts/SFCompact.ttf")

# Pydantic Models for Structured Output
class DaySchedule(BaseModel):
    tag: str
    zeit: List[str]

class WeeklySchedule(BaseModel):
    woche: str
    tage: List[DaySchedule]

# Gemini Client Setup
client = genai.Client(api_key=GEMINI_API_KEY)

async def extract_shift_plan(file_bytes: bytes, mime_type: str) -> WeeklySchedule:
    """Extracts shift plan data using Gemini 2.0 Flash."""
    prompt = f"""
    Du bist ein präziser Daten-Extraktor. Extrahiere die Arbeitszeiten für die Person {TARGET_PERSON_NAME} aus dem bereitgestellten Dienstplan. 
    Antworte ausschliesslich im JSON-Format, das dem vorgegebenen Schema entspricht.
    Wenn an einem Tag keine Arbeit stattfindet, setze Zeit auf ["Kein Einsatz"].
    Die Woche sollte im Format "TT.MM.JJJJ - TT.MM.JJJJ" angegeben werden.
    Jeder Tag sollte im Format "Wochentag TT.MM.JJJJ" (z.B. Montag 20.04.2026) angegeben werden.
    """
    
    try:
        # Use gemini-2.0-flash for high speed and accuracy
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=WeeklySchedule,
            )
        )
        
        if not response.parsed:
            logger.error(f"Gemini failed to parse the response. Raw text: {response.text}")
            raise ValueError("Gemini konnte den Schichtplan nicht im erwarteten Format extrahieren.")
            
        return response.parsed
    except Exception as e:
        logger.error(f"Error extracting shift plan: {e}")
        raise

def generate_wallpaper(schedule: WeeklySchedule) -> io.BytesIO:
    """Generates an iPhone wallpaper from the schedule."""
    # Create background (Dark mode style)
    bg_color = (15, 15, 15)
    text_color = (255, 255, 255)
    accent_color = (100, 100, 100)
    
    image = Image.new("RGB", (WALLPAPER_WIDTH, WALLPAPER_HEIGHT), color=bg_color)
    draw = ImageDraw.Draw(image)
    
    # Load fonts
    try:
        title_font = ImageFont.truetype(FONT_PATH, 80)
        day_font = ImageFont.truetype(FONT_PATH, 60)
        time_font = ImageFont.truetype(FONT_PATH, 50)
    except Exception as e:
        logger.warning(f"Could not load font from {FONT_PATH}, using default: {e}")
        title_font = ImageFont.load_default()
        day_font = ImageFont.load_default()
        time_font = ImageFont.load_default()

    # Padding and layout (Leave top 20% free for iOS clock/widgets)
    y_offset = int(WALLPAPER_HEIGHT * 0.25)
    margin = 80
    
    # Draw Week Title
    draw.text((margin, y_offset), f"Woche: {schedule.woche}", font=title_font, fill=text_color)
    y_offset += 150
    
    # Draw Days
    for day in schedule.tage:
        # Day Header
        draw.text((margin, y_offset), day.tag, font=day_font, fill=text_color)
        y_offset += 80
        
        # Times
        for time_slot in day.zeit:
            color = text_color if time_slot != "Kein Einsatz" else accent_color
            draw.text((margin + 40, y_offset), f"• {time_slot}", font=time_font, fill=color)
            y_offset += 60
        
        y_offset += 40 # Space between days
        
        # Optional: Draw a subtle separator line
        # draw.line([(margin, y_offset), (WALLPAPER_WIDTH - margin, y_offset)], fill=(40, 40, 40), width=2)
        # y_offset += 40

    # Save to buffer
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles PDF and Photo uploads."""
    if update.message.document:
        doc = update.message.document
        if doc.mime_type not in ["application/pdf", "image/jpeg", "image/png"]:
            await update.message.reply_text("Bitte sende ein PDF oder ein Bild (JPG/PNG) des Schichtplans.")
            return
        file_id = doc.file_id
        mime_type = doc.mime_type
    elif update.message.photo:
        # Get the largest photo
        photo = update.message.photo[-1]
        file_id = photo.file_id
        mime_type = "image/jpeg" # Telegram photos are usually JPEGs
    else:
        return

    status_msg = await update.message.reply_text("Verarbeite Schichtplan... ⏳")
    
    try:
        # Download file
        file = await context.bot.get_file(file_id)
        file_bytes = await file.download_as_bytearray()
        
        # Extract data
        schedule = await extract_shift_plan(bytes(file_bytes), mime_type)
        
        # Generate wallpaper
        wallpaper_buffer = generate_wallpaper(schedule)
        
        # Send back
        await status_msg.delete()
        await update.message.reply_photo(
            photo=wallpaper_buffer,
            caption=f"Hier ist dein Wallpaper für die Woche {schedule.woche} ✨"
        )
        
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await status_msg.edit_text(f"Fehler bei der Verarbeitung: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Hallo! Ich bin dein Schichtplan-Extraktor.\n\n"
        f"Sende mir ein PDF oder ein Bild deines Schichtplans, und ich erstelle dir ein "
        f"passendes iPhone-Wallpaper für {TARGET_PERSON_NAME}."
    )

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        logger.error("TELEGRAM_BOT_TOKEN and GEMINI_API_KEY must be set in .env")
        exit(1)

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    start_handler = MessageHandler(filters.COMMAND & filters.Regex('^/start$'), start)
    msg_handler = MessageHandler(filters.Document.ALL | filters.PHOTO, handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(msg_handler)
    
    logger.info("Bot started polling...")
    application.run_polling()
