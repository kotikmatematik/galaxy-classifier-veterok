from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / 'data' / 'curated_space_objects'
CSV_PATH = DATA_DIR / 'space_objects_data.csv'
EMBEDDINGS_PATH = DATA_DIR / 'space_object_embeddings.npy'
BIAS_PATH = DATA_DIR / 'space_object_person_bias.npy'
CARDS_DIR = DATA_DIR / 'cards'
TMP_DIR = ROOT_DIR / 'tmp'

MODEL_NAME = 'clip-ViT-B-32'
DEFAULT_CANDIDATE_K = 5
DEFAULT_SELECTION = 'deterministic_sample'
DEFAULT_TEMPERATURE = 0.03
DEFAULT_BIAS_STRENGTH = 1.0
