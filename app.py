import asyncio
import logging
import os

from dotenv import load_dotenv

from src.bot import run_bot
from src.matcher import SpaceObjectMatcher


def main():
    """Load configuration, initialize the matcher once, and start Telegram polling."""
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise RuntimeError('Set TELEGRAM_BOT_TOKEN in environment or .env')

    logging.info('Loading model and space-object data...')
    matcher = SpaceObjectMatcher()
    logging.info('Loaded %s objects with images. Starting Telegram polling...', len(matcher.objects_with_images))
    asyncio.run(run_bot(token, matcher))


if __name__ == '__main__':
    main()
