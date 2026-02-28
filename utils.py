
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import os

def generate_profile_card(fullname, rank, points, progress_percent, avatar_bytes=None):
    # 1. Create base image (Dark background)
    width, height = 800, 400
    background_color = (30, 30, 40) # Slightly lighter dark blue/grey
    card = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(card)

    # 2. Draw decorative elements (Gold top border)
    draw.rectangle([(0, 0), (width, 10)], fill=(255, 215, 0)) 

    # 3. Process Avatar
    avatar_size = 150
    avatar_x, avatar_y = 50, 80
    
    # Placeholder circle
    draw.ellipse((avatar_x, avatar_y, avatar_x+avatar_size, avatar_y+avatar_size), fill=(100, 100, 100))

    if avatar_bytes:
        try:
            avatar = Image.open(io.BytesIO(avatar_bytes))
            # Resize and Center Crop to Circle
            avatar = ImageOps.fit(avatar, (avatar_size, avatar_size), centering=(0.5, 0.5))
            
            # Create mask
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            
            # Paste with mask
            card.paste(avatar, (avatar_x, avatar_y), mask)
        except Exception as e:
            print(f"Avatar error: {e}")

    # 4. Load Fonts (Larger sizes)
    try:
        font_large = ImageFont.truetype("arial.ttf", 60)   # Increased
        font_medium = ImageFont.truetype("arial.ttf", 40)  # Increased
        font_small = ImageFont.truetype("arial.ttf", 30)   # Increased
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # 5. Draw Text (Shifted right to accommodate avatar)
    text_x = 250 
    draw.text((text_x, 80), f"{fullname[:20]}", font=font_large, fill=(255, 255, 255))
    draw.text((text_x, 160), f"🏅 Unvon: {rank}", font=font_medium, fill=(200, 200, 200))
    draw.text((text_x, 215), f"🧠 Zakovat: {points}", font=font_medium, fill=(200, 200, 200))

    # 6. Draw Progress Bar
    bar_x, bar_y = 50, 300
    bar_w, bar_h = 700, 40
    
    # Background bar
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], fill=(50, 50, 60))
    
    # Fill bar
    fill_w = int(bar_w * progress_percent)
    if fill_w > bar_w: fill_w = bar_w
    draw.rectangle([(bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h)], fill=(0, 255, 100)) # Green fill

    draw.text((bar_x, bar_y - 40), f"Daraja o'sishi: {int(progress_percent * 100)}%", font=font_small, fill=(255, 255, 255))

    # 7. Save to BytesIO
    output = io.BytesIO()
    card.save(output, format="PNG")
    output.seek(0)
    return output

