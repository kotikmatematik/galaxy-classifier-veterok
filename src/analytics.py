import csv
import json
from datetime import UTC, datetime

from aiogram.types import Message

from .config import ANALYTICS_PATH


FIELDNAMES = [
    'timestamp',
    'event',
    'user_id',
    'username',
    'first_name',
    'last_name',
    'language',
    'chat_id',
    'extra',
]


def log_user_event(message: Message, event: str, language: str = '', **extra):
    """Append one Telegram user event to a local CSV analytics file."""
    user = message.from_user
    ANALYTICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = ANALYTICS_PATH.exists()

    row = {
        'timestamp': datetime.now(UTC).isoformat(timespec='seconds'),
        'event': event,
        'user_id': user.id if user else '',
        'username': user.username if user else '',
        'first_name': user.first_name if user else '',
        'last_name': user.last_name if user else '',
        'language': language,
        'chat_id': message.chat.id,
        'extra': json.dumps(extra, ensure_ascii=False, sort_keys=True) if extra else '',
    }

    with ANALYTICS_PATH.open('a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
