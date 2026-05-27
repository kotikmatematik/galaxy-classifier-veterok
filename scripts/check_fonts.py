import sys
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.cards import get_font


def font_path(font):
    """Return a readable path for Pillow TrueType fonts."""
    return getattr(font, 'path', 'Pillow default bitmap font')


def main():
    """Print the fonts that will be used by the card renderer."""
    load_dotenv()
    regular_env = os.getenv('CARD_FONT_REGULAR')
    bold_env = os.getenv('CARD_FONT_BOLD')
    print(f'CARD_FONT_REGULAR: {regular_env or "not set"}')
    if regular_env:
        print(f'CARD_FONT_REGULAR exists: {Path(regular_env).exists()}')
    print(f'CARD_FONT_BOLD: {bold_env or "not set"}')
    if bold_env:
        print(f'CARD_FONT_BOLD exists: {Path(bold_env).exists()}')
    regular = get_font(22, bold=False)
    bold = get_font(32, bold=True)
    print(f'regular font: {font_path(regular)}')
    print(f'bold font: {font_path(bold)}')


if __name__ == '__main__':
    main()
