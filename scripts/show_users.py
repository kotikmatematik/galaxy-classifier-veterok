from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
EVENTS_PATH = ROOT_DIR / 'data' / 'curated_space_objects' / 'bot_events.csv'


def main():
    """Print a compact summary of Telegram users recorded by the bot."""
    if not EVENTS_PATH.exists():
        print(f'No analytics file yet: {EVENTS_PATH}')
        return

    events = pd.read_csv(EVENTS_PATH).fillna('')
    if events.empty:
        print('Analytics file exists but has no events yet.')
        return

    users = (
        events.sort_values('timestamp')
        .groupby('user_id', as_index=False)
        .agg(
            username=('username', 'last'),
            first_name=('first_name', 'last'),
            last_name=('last_name', 'last'),
            first_seen=('timestamp', 'first'),
            last_seen=('timestamp', 'last'),
            events=('event', 'count'),
        )
        .sort_values('last_seen', ascending=False)
    )

    print(f'unique users: {len(users)}')
    print(f'total events: {len(events)}')
    print(users.to_string(index=False))


if __name__ == '__main__':
    main()
