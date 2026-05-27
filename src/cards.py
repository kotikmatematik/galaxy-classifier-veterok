import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import CARDS_DIR
from .matcher import localized_value


CARD_WIDTH = 960
CARD_MAX_HEIGHT = 1800
CARD_MARGIN = 38


def get_font(size, bold=False):
    """Return a platform-available TrueType font with a safe default fallback."""
    env_path = os.getenv('CARD_FONT_BOLD' if bold else 'CARD_FONT_REGULAR')
    candidates = [
        env_path,
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/System/Library/Fonts/Supplemental/Helvetica Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Helvetica.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf',
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def safe_card_filename(text):
    """Convert object names into filesystem-safe card filename fragments."""
    text = str(text).lower().replace('&', 'and')
    text = re.sub(r'[^a-z0-9а-яё]+', '_', text)
    return text.strip('_') or 'space_object'


def crop_square(image):
    """Crop an image to the largest centered square."""
    image = image.convert('RGB')
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def square_image(image, size):
    """Return a centered square crop resized to the requested size."""
    return crop_square(image).resize((size, size), Image.Resampling.LANCZOS)


def rounded_image(image, size, radius=28):
    """Create a square image preview with rounded corners."""
    image = square_image(image, size)
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
    result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    result.paste(image, (0, 0), mask)
    return result


def draw_wrapped_text(draw, text, xy, font, fill, max_width, line_spacing=8, max_lines=None):
    """Draw wrapped text and return the next vertical drawing position."""
    words = str(text).split()
    lines = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip('.,;:') + '...'

    x, y = xy
    bbox = draw.textbbox((0, 0), 'Ag', font=font)
    line_height = (bbox[3] - bbox[1]) + line_spacing
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def create_gradient_background(size, top_color=(9, 12, 28), bottom_color=(28, 25, 50)):
    """Create a vertical RGB gradient used as the card background."""
    width, height = size
    bg = Image.new('RGB', size, top_color)
    pixels = bg.load()
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(int(top_color[i] * (1 - ratio) + bottom_color[i] * ratio) for i in range(3))
        for x in range(width):
            pixels[x, y] = color
    return bg


def create_prediction_card(person_image_path, best_row, lang='ru', output_path=None):
    """Render and save the final JPG prediction card for one matched object."""
    lang = (lang or 'ru').lower()
    person_image = Image.open(person_image_path).convert('RGB')
    object_image = Image.open(best_row.image_path).convert('RGB')

    name = localized_value(best_row, 'name', lang)
    object_type = localized_value(best_row, 'object_type', lang)
    mood = localized_value(best_row, 'mood', lang)
    description = localized_value(best_row, 'description', lang)
    match_percent = float(best_row.cosmic_match_percent)

    if lang == 'en':
        title = f'You are: {name}'
        type_label = f'Type: {object_type}'
        vibe_label = f'Vibe: {mood}'
        match_label = f'cosmic match: {match_percent:.1f}%'
        left_label = 'INPUT'
        right_label = 'MATCH'
    else:
        title = f'Ты - {name}'
        type_label = f'Тип: {object_type}'
        vibe_label = f'Вайб: {mood}'
        match_label = f'совпадение: {match_percent:.1f}%'
        left_label = 'ФОТО'
        right_label = 'ОБЪЕКТ'

    card_size = (CARD_WIDTH, CARD_MAX_HEIGHT)
    card = create_gradient_background(card_size)
    bg_object = crop_square(object_image).resize(card_size, Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(22))
    card = Image.blend(bg_object, card, alpha=0.88)
    draw = ImageDraw.Draw(card)

    frame = (CARD_MARGIN, CARD_MARGIN, CARD_WIDTH - CARD_MARGIN, CARD_MAX_HEIGHT - CARD_MARGIN)
    draw.rounded_rectangle(frame, radius=42, fill=(15, 18, 35))

    gap = 28
    y_images = 84
    x_left = CARD_MARGIN + 46
    content_w = CARD_WIDTH - 2 * CARD_MARGIN - 92
    image_size = (content_w - gap) // 2
    x_right = x_left + image_size + gap

    person_preview = rounded_image(person_image, image_size, radius=34)
    object_preview = rounded_image(object_image, image_size, radius=34)
    card.paste(person_preview, (x_left, y_images), person_preview)
    card.paste(object_preview, (x_right, y_images), object_preview)

    title_font = get_font(44, bold=True)
    meta_font = get_font(29)
    body_font = get_font(30)
    small_font = get_font(23)
    match_font = get_font(26)

    draw.text((x_left, y_images + image_size + 12), left_label, font=small_font, fill=(160, 166, 200))
    draw.text((x_right, y_images + image_size + 12), right_label, font=small_font, fill=(160, 166, 200))

    y = y_images + image_size + 58
    content_x = CARD_MARGIN + 46
    y = draw_wrapped_text(draw, title, (content_x, y), title_font, (255, 255, 255), content_w, line_spacing=10, max_lines=2)
    y += 14
    draw.text((content_x, y), match_label, font=match_font, fill=(165, 154, 232))
    y += 46
    y = draw_wrapped_text(draw, type_label, (content_x, y), meta_font, (210, 215, 244), content_w, line_spacing=9, max_lines=2)
    y += 6
    y = draw_wrapped_text(draw, vibe_label, (content_x, y), meta_font, (210, 215, 244), content_w, line_spacing=9, max_lines=3)
    y += 22
    draw.line((content_x, y, content_x + content_w, y), fill=(78, 82, 118), width=1)
    y += 28
    y = draw_wrapped_text(draw, description, (content_x, y), body_font, (238, 240, 255), content_w, line_spacing=11, max_lines=5)

    final_height = min(CARD_MAX_HEIGHT, max(980, int(y + CARD_MARGIN + 42)))
    card = card.crop((0, 0, CARD_WIDTH, final_height))
    neutral_bg = Image.new('RGB', (CARD_WIDTH, final_height), (9, 12, 28))
    panel_mask = Image.new('L', (CARD_WIDTH, final_height), 0)
    mask_draw = ImageDraw.Draw(panel_mask)
    mask_draw.rounded_rectangle(
        (CARD_MARGIN, CARD_MARGIN, CARD_WIDTH - CARD_MARGIN, final_height - CARD_MARGIN),
        radius=42,
        fill=255,
    )
    neutral_bg.paste(card, (0, 0), panel_mask)
    card = neutral_bg
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        (CARD_MARGIN, CARD_MARGIN, CARD_WIDTH - CARD_MARGIN, final_height - CARD_MARGIN),
        radius=42,
        outline=(87, 80, 132),
        width=2,
    )

    if output_path is None:
        output_path = CARDS_DIR / f"card_{Path(person_image_path).stem}_{safe_card_filename(str(name))}_{lang}.jpg"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card.save(output_path, format='JPEG', quality=94)
    return output_path
