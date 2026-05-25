import io
import os
import logging
from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger(__name__)

def generate_wallpaper(schedule: dict, width: int, height: int, font_path: str) -> io.BytesIO:
    """Generates an iPhone wallpaper with an optional custom background."""
    bg_color = (15, 15, 15)
    text_color = (255, 255, 255)
    accent_color = (140, 140, 140) # Slightly lighter for better contrast on images
    
    # Try to load a custom background image
    image = None
    bg_dir = "./background-image"
    if os.path.exists(bg_dir):
        files = [f for f in os.listdir(bg_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if files:
            try:
                bg_path = os.path.join(bg_dir, files[0])
                bg_img = Image.open(bg_path).convert("RGB")
                # Resize and crop to fill the target dimensions (Aspect Fill)
                image = ImageOps.fit(bg_img, (width, height))
                logger.info(f"Using custom background: {bg_path}")
                
                # Optional: Add a subtle dark overlay to ensure text readability
                overlay = Image.new("RGBA", (width, height), (0, 0, 0, 140)) # 140/255 opacity
                image.paste(overlay, (0, 0), overlay)
            except Exception as e:
                logger.error(f"Failed to load custom background: {e}")

    # Fallback to solid color if no image found or failed to load
    if image is None:
        image = Image.new("RGB", (width, height), color=bg_color)
    
    draw = ImageDraw.Draw(image)
    
    # Stylistic configuration
    TITLE_SIZE = 55
    DAY_SIZE = 45
    TIME_SIZE = 38
    TOP_MARGIN_FIXED = 700  # Fixed pixel margin from top
    LEFT_MARGIN = 100
    
    # Load fonts (using standard weights for cleaner look)
    try:
        title_font = ImageFont.truetype(font_path, TITLE_SIZE)
        day_font = ImageFont.truetype(font_path, DAY_SIZE)
        time_font = ImageFont.truetype(font_path, TIME_SIZE)
    except Exception as e:
        logger.warning(f"Font loading failed: {e}")
        title_font = ImageFont.load_default()
        day_font = ImageFont.load_default()
        time_font = ImageFont.load_default()

    y_offset = TOP_MARGIN_FIXED
    
    # Draw Days
    for day in schedule.get('tage', []):
        tag_text = day.get('tag', '')
        stunden = day.get('stunden', '0h')
        
        # Format: Montag 30. März (9.25h)
        full_header = f"{tag_text} -- {stunden}"
        
        draw.text((LEFT_MARGIN, y_offset), full_header, font=day_font, fill=text_color)
        y_offset += 70
        
        for time_slot in day.get('zeit', []):
            color = text_color if time_slot != "Kein Einsatz" else accent_color
            draw.text((LEFT_MARGIN + 30, y_offset), f" {time_slot}", font=time_font, fill=color)
            y_offset += 55
        
        y_offset += 50

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr
