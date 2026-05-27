# Operations

Common commands for maintaining the deployed bot.

## Manual Run

```bash
cd /root/galaxy-matching-veterok
source .venv/bin/activate
python app.py
```

Stop a manual run with `Ctrl+C`.

## Systemd Run

```bash
systemctl status spacebot
systemctl restart spacebot
journalctl -u spacebot -f
```

## Deploy Updated Code

Run from the local project directory:

```bash
rsync -av \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.DS_Store' \
  --exclude 'tmp' \
  ./ root@SERVER_IP:/root/galaxy-matching-veterok/
```

Then restart the service on the server:

```bash
systemctl restart spacebot
```

## Health Checks

```bash
cd /root/galaxy-matching-veterok
source .venv/bin/activate
python scripts/check_runtime.py
python scripts/check_fonts.py
```

## User Activity

The bot stores local event logs in `data/curated_space_objects/bot_events.csv`.

Show a user summary:

```bash
python scripts/show_users.py
```

Inspect recent events:

```bash
tail -n 20 data/curated_space_objects/bot_events.csv
```

Do not publish this CSV. It contains Telegram user IDs and usernames.
