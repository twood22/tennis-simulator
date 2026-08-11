# Repository guidance

## Architecture

- `api/index.py` is the canonical Flask entry point; `app.py` only imports it.
- `simulation_service.py` owns request validation and orchestration.
- `simulation_engine.py` owns point, game, set, match, and Monte Carlo logic.
- `data_loader.py` loads the reviewed aggregate CSV snapshot without pandas.
- `scripts/refresh_data.py` creates the snapshot from rolling raw match totals.

Keep the model layer dependency-free. Do not add a second API implementation or
special-case scoring logic in a route.

## Data

The four filenames under `data/` are legacy names retained for compatibility;
their current contents are generated from the MIT-licensed TennisMyLife match
database. `data/metadata.json` is the provenance record. Missing surface samples
fall back to all-surface data before hard-court data and must produce a warning.

Run a refresh with `python scripts/refresh_data.py`. The script must stage and
validate a complete snapshot before replacing tracked data. Never hand-edit a
single generated CSV without regenerating and validating all four.

## Verification

```bash
python -m unittest discover -s tests -v
python -m py_compile app.py api/index.py data_loader.py simulation_engine.py simulation_service.py scripts/refresh_data.py tests/*.py
git diff --check
```

For a scoring change, add a deterministic regression test. Preserve optional
seeds so reported simulations can be reproduced.

## Scope

The current model deliberately avoids opponent-strength adjustment, recency
weighting, hierarchical shrinkage, and posterior uncertainty. Those ideas live
in `FUTURE_TODOS.md`; do not slip them into an unrelated correctness change.
