# Deployment

This directory contains deployment helpers for running the bot on an Ubuntu server.

## Copy Project

From your local project directory, copy files without local virtualenv/cache files:

```bash
rsync -av \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.DS_Store' \
  --exclude 'tmp' \
  ./ user@IP:/home/user/galaxy-matching-veterok/
```

## Ubuntu Setup

Install basic Python tooling:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip fonts-dejavu-core fonts-liberation2
```

Go to the project directory:

```bash
cd /home/user/galaxy-matching-veterok
```

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r requirements.txt
```

Install CPU-only `torch` before `sentence-transformers` dependencies. Otherwise pip may install large NVIDIA/CUDA packages that are not needed for this bot on a CPU server.

Set the bot token:

```bash
nano .env
```

The file must contain:

```bash
TELEGRAM_BOT_TOKEN=your_token_from_botfather
```

Test the bot manually:

```bash
python scripts/check_runtime.py
python scripts/check_fonts.py
python app.py
```

If `scripts/check_fonts.py` prints `Pillow default bitmap font`, install the font packages above or set explicit font paths in `.env`:

```bash
CARD_FONT_REGULAR=/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf
CARD_FONT_BOLD=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf
```

Run `python scripts/check_fonts.py` after changing `.env`; it prints the final font files used by Pillow.

## Systemd Service

Before installing the service, edit `deploy/spacebot.service.example` and replace:

- `user` with the real Linux user.
- `/home/user/galaxy-matching-veterok` with the real project path.

Install and start the service:

```bash
sudo cp deploy/spacebot.service.example /etc/systemd/system/spacebot.service
sudo systemctl daemon-reload
sudo systemctl enable spacebot
sudo systemctl start spacebot
sudo systemctl status spacebot
```

View live logs:

```bash
journalctl -u spacebot -f
```

Restart after code changes:

```bash
sudo systemctl restart spacebot
```
