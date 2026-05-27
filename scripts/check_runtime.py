from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / '.env'
DATA_DIR = ROOT_DIR / 'data' / 'curated_space_objects'
CSV_PATH = DATA_DIR / 'space_objects_data.csv'
EMBEDDINGS_PATH = DATA_DIR / 'space_object_embeddings.npy'
BIAS_PATH = DATA_DIR / 'space_object_person_bias.npy'
IMAGE_DIR = DATA_DIR / 'images'


def read_env_token():
    """Read the Telegram bot token from the local .env file without printing it."""
    if not ENV_PATH.exists():
        return ''
    for line in ENV_PATH.read_text().splitlines():
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            return line.split('=', 1)[1].strip()
    return ''


def main():
    """Validate local runtime files required before starting the Telegram bot."""
    token = read_env_token()
    if not token:
        raise RuntimeError('Missing TELEGRAM_BOT_TOKEN in .env')

    for path in [CSV_PATH, EMBEDDINGS_PATH, BIAS_PATH, IMAGE_DIR]:
        if not path.exists():
            raise RuntimeError(f'Missing required path: {path.relative_to(ROOT_DIR)}')

    objects_df = pd.read_csv(CSV_PATH).fillna('')
    if 'image_path' not in objects_df.columns:
        raise RuntimeError('CSV is missing image_path column')

    missing_images = [path for path in objects_df['image_path'] if not (ROOT_DIR / path).exists()]
    if missing_images:
        raise RuntimeError(f'Missing object images: {len(missing_images)}')

    embeddings = np.load(EMBEDDINGS_PATH)
    bias = np.load(BIAS_PATH)
    if len(embeddings) != len(objects_df):
        raise RuntimeError(f'Embeddings length {len(embeddings)} does not match CSV rows {len(objects_df)}')
    if len(bias) != len(objects_df):
        raise RuntimeError(f'Bias length {len(bias)} does not match CSV rows {len(objects_df)}')

    print('runtime check ok')
    print(f'objects: {len(objects_df)}')
    print(f'embeddings: {embeddings.shape}')
    print('telegram token: configured')


if __name__ == '__main__':
    main()
