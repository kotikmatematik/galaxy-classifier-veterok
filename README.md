# Space Object Telegram Bot

A Telegram bot that asks the user for a card language, accepts a portrait photo, matches it to a curated space object with CLIP embeddings, and returns a generated JPG card.

The original notebook logic has been moved into regular Python modules so the project can run as a deployable bot.

## Features

- Telegram bot powered by `aiogram` polling.
- Language selection before card generation: Russian or English.
- Photo download, temporary file handling, prediction, card generation, and cleanup.
- CLIP model loaded once at startup with `sentence-transformers`.
- Precomputed object embeddings and person-bias calibration loaded from local files.
- Systemd service example for Ubuntu servers.

## Project Structure

- `app.py` - main entrypoint; loads `.env`, initializes the matcher, and starts polling.
- `src/bot.py` - Telegram conversation flow.
- `src/matcher.py` - CLIP matching and scoring logic.
- `src/cards.py` - JPG card rendering.
- `src/config.py` - project paths and runtime defaults.
- `data/curated_space_objects/space_objects_data.csv` - object metadata.
- `data/curated_space_objects/space_object_embeddings.npy` - precomputed object embeddings.
- `data/curated_space_objects/space_object_person_bias.npy` - calibration bias.
- `data/curated_space_objects/images/` - local object images.
- `archive/` - old notebooks kept for reference.
- `deploy/` - deployment notes and systemd example.

## Requirements

- Python 3.10 or newer.
- Internet access on first run so `sentence-transformers` can download `clip-ViT-B-32`.
- A Telegram bot token from BotFather.
- Enough disk space for Python dependencies and the model cache.
- `fonts-dejavu-core` or `fonts-liberation2` on Linux for good-looking card typography.

## Entrypoint

Run the project with `python app.py`.

`app.py` is intentionally small. It loads environment variables, reads `TELEGRAM_BOT_TOKEN`, initializes `SpaceObjectMatcher` once so the CLIP model and `.npy` files stay in memory, and then starts Telegram polling through `src/bot.py`.

## Local Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Set the Telegram token in `.env`:

```bash
TELEGRAM_BOT_TOKEN=your_token_from_botfather
```

Run the bot:

```bash
python app.py
```

## Runtime Data Checklist

These files must exist before starting the bot:

- `data/curated_space_objects/space_objects_data.csv`
- `data/curated_space_objects/space_object_embeddings.npy`
- `data/curated_space_objects/space_object_person_bias.npy`
- `data/curated_space_objects/images/`

Generated cards are written to `data/curated_space_objects/cards/`. Temporary Telegram photos are written to `tmp/`. Both are ignored by git.

## Deployment

Copy the project to a server without local virtualenv/cache files:

```bash
rsync -av \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.DS_Store' \
  --exclude 'tmp' \
  ./ user@IP:/home/user/spacebot/
```

Install and test on the server:

```bash
ssh user@IP
cd /home/user/spacebot
sudo apt update
sudo apt install -y python3-venv python3-pip fonts-dejavu-core fonts-liberation2
python3 -m venv .venv
source .venv/bin/activate
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r requirements.txt
nano .env
python scripts/check_runtime.py
python scripts/check_fonts.py
python app.py
```

The explicit CPU-only `torch` install prevents pip from downloading large NVIDIA/CUDA packages on a regular CPU server.

If the generated cards use an ugly fallback font, run `python scripts/check_fonts.py` on the server. You can override fonts in `.env`:

```bash
CARD_FONT_REGULAR=/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf
CARD_FONT_BOLD=/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf
```

After a manual test succeeds, configure systemd using `deploy/spacebot.service.example`.

## Systemd

Edit `deploy/spacebot.service.example` and replace `user` and `/home/user/spacebot` with the real server user and project path.

Then install the service:

```bash
sudo cp deploy/spacebot.service.example /etc/systemd/system/spacebot.service
sudo systemctl daemon-reload
sudo systemctl enable spacebot
sudo systemctl start spacebot
sudo systemctl status spacebot
```

View logs:

```bash
journalctl -u spacebot -f
```

## Development Checks

Run the runtime checklist:

```bash
python scripts/check_runtime.py
```

Check Python syntax:

```bash
python3 -m compileall app.py src scripts
```

Check that CSV image paths resolve:

```bash
python3 - <<'PY'
from pathlib import Path
import pandas as pd

root = Path.cwd()
df = pd.read_csv(root / 'data' / 'curated_space_objects' / 'space_objects_data.csv').fillna('')
missing = [p for p in df['image_path'] if not (root / p).exists()]
print(f'objects: {len(df)}')
print(f'missing images: {len(missing)}')
PY
```

## Notes

- Do not commit `.env`; it contains the real Telegram token and is ignored by git.
- The match percentage is a playful presentation score, not a scientific probability.
- The bot uses polling, so no domain name, TLS certificate, or webhook setup is required.
