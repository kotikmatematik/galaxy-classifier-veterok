# AGENTS.md

## Repo Shape
- Main working notebook: `curated_space_objects_dataset.ipynb`; it contains the final curated space-object matcher and card generator.
- `efficientnet_galaxy_zoo.ipynb` is exploratory Galaxy Zoo/EfficientNet work, not the final product pipeline.
- There is no `README`, package manifest, CI, or test runner config; verify notebook changes with a Python syntax pass over code cells.

## Data Sources
- Final metadata source of truth: `data/curated_space_objects/space_objects_data.csv`.
- Final CSV columns currently expected by the notebook: `name_en`, `name_ru`, `mood_en`, `mood_ru`, `description_en`, `description_ru`, `object_type_en`, `object_type_ru`, `image_path`.
- Do not reintroduce `description_en_updated` or `description_ru_updated`; the active code uses `description_en` / `description_ru`.
- Object image paths in the CSV must exist locally under `data/curated_space_objects/images/`; missing images reduce `objects_with_images`, embeddings, calibration, and prediction coverage.
- Cached/generated files used by the active notebook include `space_object_embeddings.npy`, `space_object_person_bias.npy`, `cards/`, `calibration_people/`, and `test_people/`.

## Notebook Workflow
- Install dependencies from the first cell when needed: `pandas numpy matplotlib pillow requests tqdm scikit-learn sentence-transformers`; `deep-translator` is only for archived translation cells.
- Active CLIP model: `SentenceTransformer('clip-ViT-B-32')` from `sentence-transformers`.
- Normal pipeline starts from `FINAL_CSV_PATH`; archive Wikipedia/translation build cells are guarded by `RUN_ARCHIVE_DATASET_BUILD = False` and should stay off unless explicitly requested.
- Download flags are explicit knobs: `DOWNLOAD_OBJECT_IMAGES`, `DOWNLOAD_CALIBRATION_PEOPLE`, and `DOWNLOAD_TEST_PEOPLE`; check them before running cells that may fetch external data.
- If matching suddenly covers far fewer than the CSV row count, inspect `objects_df['has_image']` before changing model logic.

## Matching/Card Logic
- Public prediction/card calls no longer use `top_k`; use `candidate_k` to control the candidate pool.
- Less-random product setting currently preferred: `selection='deterministic_sample'`, `candidate_k=5` or `10`, `temperature=0.03`.
- `selection='best'` is closest to pure CLIP ranking; `selection='deterministic_diverse_sample'` is more diverse but farther from score-based matching.
- `bias_strength` controls how strongly calibration suppresses objects that match generic face photos; keep it tunable while testing distribution.
- `OBJECT_SCORE_PENALTIES` contains manual soft penalties such as `Tycho's Supernova`; these are not bans and should remain small.
- `cosmic_match_percent` is a presentation score derived from adjusted scores plus small deterministic jitter, not a calibrated probability.

## Verification
- Validate notebook syntax after edits with:
```bash
python3 - <<'PY'
import ast, json
from pathlib import Path
nb = json.loads(Path('curated_space_objects_dataset.ipynb').read_text())
for i, cell in enumerate(nb.get('cells', [])):
    if cell.get('cell_type') != 'code':
        continue
    src = ''.join('\n' if line.lstrip().startswith(('!', '%')) else line for line in cell.get('source', [])) or '\n'
    ast.parse(src)
print('notebook code syntax ok')
PY
```
- Avoid relying on `jupyter nbconvert --clear-output` in this environment; it has failed due a local `jupyter_contrib_nbextensions` import issue.
