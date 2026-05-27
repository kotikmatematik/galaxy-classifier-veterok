import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from .config import BIAS_PATH, CSV_PATH, EMBEDDINGS_PATH, MODEL_NAME


REQUIRED_COLUMNS = [
    'name_en', 'name_ru', 'description_en', 'description_ru',
    'object_type_en', 'object_type_ru', 'mood_en', 'mood_ru', 'image_path',
]

OBJECT_SCORE_PENALTIES = {
    "Tycho's Supernova": 0.01,
    'Сверхновая Тихо': 0.01,
}


@dataclass(frozen=True)
class MatchSettings:
    candidate_k: int | None = 5
    bias_strength: float = 1.0
    selection: str = 'deterministic_sample'
    temperature: float = 0.03


def localized_value(row, base_name, lang='ru'):
    """Read a localized field from a pandas row with English fallback columns."""
    lang = (lang or 'ru').lower()
    col = f'{base_name}_ru' if lang == 'ru' else f'{base_name}_en'
    if hasattr(row, 'get'):
        value = row.get(col, '')
        if isinstance(value, str) and value:
            return value
        return row.get(base_name, '')
    value = getattr(row, col, '')
    if isinstance(value, str) and value:
        return value
    return getattr(row, base_name, '')


def deterministic_seed_from_image(image):
    """Build a stable numeric seed from image pixels for deterministic sampling."""
    normalized = image.convert('RGB').resize((128, 128))
    digest = hashlib.sha256(normalized.tobytes()).digest()
    return int.from_bytes(digest[:8], byteorder='big', signed=False)


def deterministic_jitter(seed, name, low=-3.5, high=3.5):
    """Return a stable pseudo-random jitter for one image/object pair."""
    digest = hashlib.sha256(f'{seed}:{name}'.encode('utf-8')).digest()
    value = int.from_bytes(digest[:8], byteorder='big', signed=False) / 2**64
    return low + (high - low) * value


def add_fun_match_scores(results, all_adjusted_scores, image_seed):
    """Add presentation-oriented match percentages and score diagnostics."""
    results = results.copy()
    all_scores = np.asarray(all_adjusted_scores, dtype=float)
    selected_scores = results['adjusted_score'].to_numpy(dtype=float)

    mean = all_scores.mean()
    std = all_scores.std()
    z_scores = np.zeros_like(selected_scores) if std < 1e-9 else (selected_scores - mean) / std

    percentiles = np.asarray([float((all_scores <= value).mean()) for value in selected_scores])
    z_component = 1 / (1 + np.exp(-(z_scores - 0.50) / 0.90))
    percentile_component = np.clip((percentiles - 0.60) / 0.40, 0, 1)
    combined = 0.35 * z_component + 0.65 * percentile_component

    base_percent = 72 + 22 * combined
    standout_bonus = np.clip((z_scores - 2.0) * 2.5, 0, 4)
    rank_penalty = np.minimum(np.arange(len(results)) * 0.65, 5.0)
    jitters = np.asarray([deterministic_jitter(image_seed, name, low=-1.5, high=1.5) for name in results['name']])

    results['cosmic_match_percent'] = np.clip(base_percent + standout_bonus - rank_penalty + jitters, 72, 96)
    results['score_percentile'] = percentiles
    results['score_z'] = z_scores
    return results


def softmax(values, temperature=0.03):
    """Compute a temperature-scaled softmax over candidate scores."""
    values = np.asarray(values, dtype=np.float64) / max(temperature, 1e-6)
    values = values - values.max()
    exp_values = np.exp(values)
    return exp_values / exp_values.sum()


def selected_candidate_position(results, image_seed, selection='best', temperature=0.03):
    """Choose the displayed candidate according to the configured selection mode."""
    if len(results) <= 1 or selection == 'best':
        return 0

    if selection in {'sample', 'deterministic_sample'}:
        probabilities = softmax(results['adjusted_score'].to_numpy(), temperature=temperature)
    elif selection in {'diverse_sample', 'deterministic_diverse_sample'}:
        ranks = np.arange(len(results), dtype=np.float64)
        probabilities = 1 / np.power(ranks + 1, 1.15)
        probabilities = probabilities / probabilities.sum()
    else:
        return 0

    if selection.startswith('deterministic_'):
        rng = np.random.default_rng(image_seed)
        return int(rng.choice(len(results), p=probabilities))
    return int(np.random.choice(len(results), p=probabilities))


def candidate_count_for_selection(candidate_k=None, selection='best'):
    """Resolve the candidate pool size for the selected ranking strategy."""
    if candidate_k is not None:
        return candidate_k
    if selection in {'diverse_sample', 'deterministic_diverse_sample'}:
        return 30
    return 5


class SpaceObjectMatcher:
    """Load CLIP assets once and predict matching space objects for user photos."""

    def __init__(self, model_name=MODEL_NAME, csv_path=CSV_PATH, embeddings_path=EMBEDDINGS_PATH, bias_path=BIAS_PATH):
        self.csv_path = Path(csv_path)
        self.embeddings_path = Path(embeddings_path)
        self.bias_path = Path(bias_path)
        self.model = SentenceTransformer(model_name)
        self.objects_df = self._load_objects()
        self.objects_with_images = self.objects_df[self.objects_df['has_image']].reset_index(drop=True)
        if self.objects_with_images.empty:
            raise ValueError('No objects with local images found. Check image_path values in the CSV.')
        self.space_embeddings = self._load_embeddings()
        self.person_bias = self._load_person_bias()

    def _load_objects(self):
        """Load metadata, validate required columns, and resolve image paths."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f'Missing CSV file: {self.csv_path}')
        objects_df = pd.read_csv(self.csv_path).fillna('')
        missing_cols = sorted(set(REQUIRED_COLUMNS) - set(objects_df.columns))
        if missing_cols:
            raise ValueError(f'Missing columns in final CSV: {missing_cols}')

        for base_col, en_col in [
            ('name', 'name_en'),
            ('object_type', 'object_type_en'),
            ('description', 'description_en'),
            ('mood', 'mood_en'),
        ]:
            if base_col not in objects_df.columns:
                objects_df[base_col] = objects_df[en_col]

        objects_df['image_path'] = objects_df['image_path'].map(lambda p: str((self.csv_path.parents[2] / p).resolve()) if p else '')
        objects_df['has_image'] = objects_df['image_path'].map(lambda p: bool(p) and Path(p).exists())
        return objects_df

    def _load_embeddings(self):
        """Load precomputed object embeddings and validate their row count."""
        if not self.embeddings_path.exists():
            raise FileNotFoundError(f'Missing embeddings file: {self.embeddings_path}')
        embeddings = np.load(self.embeddings_path)
        if len(embeddings) != len(self.objects_with_images):
            raise ValueError(
                f'Embeddings length {len(embeddings)} does not match objects with images {len(self.objects_with_images)}.'
            )
        return embeddings

    def _load_person_bias(self):
        """Load calibration bias or fall back to zero bias when absent."""
        if not self.bias_path.exists():
            return np.zeros(len(self.objects_with_images), dtype=np.float32)
        person_bias = np.load(self.bias_path)
        if len(person_bias) != len(self.space_embeddings):
            raise ValueError(
                f'person_bias length {len(person_bias)} does not match embeddings length {len(self.space_embeddings)}.'
            )
        return person_bias

    def object_score_penalties(self):
        """Return small manual penalties for objects that should be softened."""
        penalties = np.zeros(len(self.objects_with_images), dtype=float)
        for name, penalty in OBJECT_SCORE_PENALTIES.items():
            for col in ['name_en', 'name_ru', 'name']:
                if col in self.objects_with_images.columns:
                    penalties = np.where(
                        self.objects_with_images[col] == name,
                        np.maximum(penalties, penalty),
                        penalties,
                    )
        return penalties

    def adjusted_scores_with_person_bias(self, raw_scores, bias_strength=1.0, penalty_cap=0.1):
        """Subtract centered face-photo bias from raw CLIP similarities."""
        centered_bias = self.person_bias - np.mean(self.person_bias)
        bias_penalty = bias_strength * np.clip(centered_bias, 0, None)
        bias_penalty = np.clip(bias_penalty, 0, penalty_cap)
        return raw_scores - bias_penalty, bias_penalty

    def predict_space_object_raw(self, image_path, settings=None):
        """Predict the best matching object and return the full candidate table."""
        settings = settings or MatchSettings()
        query_image = Image.open(image_path).convert('RGB')
        image_seed = deterministic_seed_from_image(query_image)
        query_embedding = self.model.encode([query_image], convert_to_numpy=True, normalize_embeddings=True)
        raw_scores = cosine_similarity(query_embedding, self.space_embeddings)[0]

        scores, _ = self.adjusted_scores_with_person_bias(raw_scores, bias_strength=settings.bias_strength)
        object_penalty = self.object_score_penalties()
        scores = scores - object_penalty

        candidate_k = candidate_count_for_selection(settings.candidate_k, settings.selection)
        top_indices = np.argsort(scores)[::-1][:candidate_k]
        results = self.objects_with_images.iloc[top_indices].copy()
        results['raw_score'] = raw_scores[top_indices]
        results['adjusted_score'] = scores[top_indices]
        results['object_penalty'] = object_penalty[top_indices]
        results = add_fun_match_scores(results, scores, image_seed)

        selected_pos = selected_candidate_position(results, image_seed, settings.selection, settings.temperature)
        best = results.iloc[selected_pos]
        return best, results, query_image
