# Lost in Translation

Current complexity study, prepared for Klara and Luisa on 15 November 2026.
Read [HANDOVER.md](HANDOVER.md) first for the research question, completed work,
limitations and next tasks. This is a local Git repository with an initial snapshot
commit. No remote repository has been created or published.

## What is ready

- Historical analysis: 10,581 official German motion justifications, 2000-2025.
- Translation sample: 260 pairs, ten per year; 259 completed outputs and one
  preserved failed attempt (20013159). Completion is not a quality guarantee.
- Main expanded paired comparison: NOT SCORED YET. The comparison script
  deliberately refuses input containing unresolved `failed_records`.
- Existing ten-document development and twenty-document validation results are
  included as preliminary evidence, not results for the expanded sample.

## Open the project

Unzip the archive and open the `lost-in-translation` folder in your editor.
Run all commands below from that folder. Paths are relative to this repository;
there is no outer `NLP/lost_in_translation` directory in this package.

```bash
git status
git log -1 --oneline
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The recorded working environment uses Python 3.14.7 on Apple Silicon macOS.
Use that version where possible. Other Python/OS combinations have not been
validated. `environment_versions.json` records observed direct dependencies;
this is not a complete transitive lockfile. Downloads require internet access.
The optional translation dependencies are not needed for analysing saved output.

## Unpack the detailed historical results

The 177 MB JSON is stored losslessly as gzip, to keep the tracked file small.
The unpacked file is ignored by Git; retain the gzip snapshot.

```bash
python - <<'PYCODE'
import gzip
import shutil
from pathlib import Path

folder = Path("data/processed")
with gzip.open(folder / "historical_complexity.json.gz", "rb") as source:
    with (folder / "historical_complexity.json").open("wb") as target:
        shutil.copyfileobj(source, target)
PYCODE
```

The chart is already available at `docs/figures/historical_complexity.png`.
To redraw it from the saved measurements without rescoring:

```bash
python - <<'PYCODE'
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from score_historical_complexity import plot_history

plot_history(Path("."))
PYCODE
```

## Reproduce the data and analyses

These commands overwrite their derived outputs. Work on a branch and inspect
`git diff` before committing. The scripts reuse the bundled raw snapshots; a
normal rerun therefore does not fetch a new corpus silently.

```bash
python scripts/audit_motion_coverage.py
python scripts/prepare_expanded_sample.py
python scripts/score_historical_complexity.py
```

The last command reparses all 10,581 documents and recreates the figure. It can
take several minutes. It uses the shared `load_parser` and `measure_text` functions
from `scripts/compare_complexity.py`.

To reproduce the twenty-document preliminary validation result:

```bash
python - <<'PYCODE'
from pathlib import Path
from scripts.compare_complexity import compare_complexity

compare_complexity(
    Path("."),
    input_name="complexity_validation_translations.json",
    output_name="complexity_validation_results.json",
)
PYCODE
```

For the expanded comparison, first document a decision about the failed case
and finish output-quality checks. Do not delete the failure merely to bypass
the guard. A clearly labelled analysis of the 259 completed pairs is possible,
but its failure/exclusion policy must be implemented and reported explicitly.
There is currently no dedicated command implementing that policy.

## Optional: run the local translator

Not needed for Luisa to start analysing the existing data.

```bash
python -m pip install -r requirements-translation.txt
mkdir -p models
```

Obtain `translategemma-4b-it-Q4_K_M.gguf` from
https://huggingface.co/Menterium/translategemma-4b-it-GGUF
and place it in `models/`. Expected SHA256:
`e7d9523174272fca61264b339f06d10c6115426267bb0f752b0124084e487b8e`.
Check the model's licence and access conditions at its source. This ZIP does not
redistribute weights. `llama-cpp-python` may require a platform-specific build;
the recorded setup uses Apple Metal (`n_gpu_layers=-1`). Other hardware is not
configured or tested here.

```bash
python - <<'PYCODE'
from pathlib import Path
from scripts.translate_pilot import translate_pilot

translate_pilot(
    Path("."),
    input_name="complexity_expanded_pairs.json",
    output_name="complexity_expanded_translations.json",
)
PYCODE
```

On the bundled completed attempt set this reports no unattempted documents.
It deliberately does NOT retry the flagged failure automatically. It preserves
successful and failed attempts separately and validates saved input/settings.
Use a new, documented output for any changed translation method. Running
`translate_pilot.py` directly uses an obsolete pilot default whose inputs are not
bundled; always use the explicit call above for this study.

## Collaborate with Git

This repository has no remote. To collaborate online, create an empty private
repository in your chosen hosting account, then add its URL and push `main`.
No account credentials are included in this ZIP. Set your own Git author name
and email before making commits.

```bash
git switch -c luisa/historical-analysis
# Make focused changes, then inspect them:
git status
git diff
# Add only the intended files and commit your work.
```

Once a shared remote is configured, pull before starting and push your branch.
Avoid editing the same script simultaneously. Keep the fixed inputs and saved
translation outputs unchanged; save new analysis outputs under new names.

## File integrity and scope

`SHA256SUMS` records the packaged files before the initial Git commit; `.git`
and `SHA256SUMS` itself are excluded. On macOS, verify with
`shasum -a 256 -c SHA256SUMS`; on Linux use `sha256sum -c SHA256SUMS`.

The package omits weights, virtual environments, caches, access tokens, abandoned
sentiment/quality code and superseded data. The unabridged methods log retains
historical references to those experiments; they are not required dependencies.
No project licence has been chosen on your behalf. Public release and the course's
open-source requirement still require an explicit licensing decision and respect
for the source data/model terms.
