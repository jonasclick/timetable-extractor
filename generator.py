import io
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

def generate_wallpaper(schedule: dict, width: int, height: int, font_path: str) -> io.BytesIO:
    """Generates an iPhone wallpaper from the schedule dict."""
    bg_color = (15, 15, 15)
    text_color = (255, 255, 255)
    accent_color = (100, 100, 100)
    
    image = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(image)
    
    try:
        title_font = ImageFont.truetype(font_path, 80)
        day_font = ImageFont.truetype(font_path, 60)
        time_font = ImageFont.truetype(font_path, 50)
    except Exception as e:
        logger.warning(f"Font loading failed: {e}")
        title_font = ImageFont.load_default()
        day_font = ImageFont.load_default()
        time_font = ImageFont.load_default()

    y_offset = int(height * 0.25)
    margin = 80
    
    # Draw Week Title
    draw.text((margin, y_offset), f"Woche: {schedule.get('woche', 'Unbekannt')}", font=title_font, fill=text_color)
    y_offset += 150
    
    # Draw Days
    for day in schedule.get('tage', []):
        draw.text((margin, y_offset), day.get('tag', ''), font=day_font, fill=text_color)
        y_offset += 80
        
        for time_slot in day.get('zeit', []):
            color = text_color if time_slot != "Kein Einsatz" else accent_color
            draw.text((margin + 40, y_offset), f"• {time_slot}", font=time_font, fill=color)
            y_offset += 60
        
        y_offset += 40

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr
