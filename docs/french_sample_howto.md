# French-authored sample: how to run it

**Why.** In the original 260-motion sample, only 63 motions were submitted by
French-speaking members. For most others the official German is the original,
so the model translated a translation back (German → French → German). This
sample keeps only French-authored motions, so the comparison is official
German translation vs. machine translation of the same French original.

**Author language** (`data/processed/french_authored_motions.csv`): Curia Vista
does not record the original language, and `Person.NativeLanguage` is empty.
We use the submitting member's canton (VD, NE, GE, JU = French), and for
bilingual cantons (BE, FR, VS, GR) the language of the member's biography text.
That text matched the canton language in 140 of 140 members from monolingual
cantons. Committees and parliamentary groups are excluded. This is a proxy.

**Sample** (`scripts/prepare_french_sample.py`, already run; result committed):
10 French-authored motions per year 2000–2025 (260), development documents
excluded. The 63 French-authored motions already translated are reused, and
197 are new. The script refuses to overwrite an existing sample.

## Reproduce the analysis

From the repository root, with the analysis environment activated:

```bash
bash reproduce.sh
```

This uses the 259 saved translations and the recorded failed attempt. It does
not load the translation model or generate new translations. The failed text
(20003342) used 2,037 prompt tokens and reached the 1,800-token output limit
(`finish_reason: length`); it did not exceed the input limit.

## Generate a separate translation run (optional)

1. Install `requirements-translation.txt` and download the model as described in
   the README under "Regenerating the machine translations (optional)". Check
   the model checksum before running it.
2. Generate into a separate file to preserve the submitted results:

   ```bash
   python - <<'PYCODE'
   from pathlib import Path
   from scripts.translate_pilot import translate_pilot
   translate_pilot(
       Path("."),
       input_name="complexity_fr_author_pairs.json",
       output_name="complexity_fr_author_translations_rerun.json",
       record_over_limit=True,
   )
   PYCODE
   ```

   This attempts all 260 texts and resumes from the separate file if interrupted.
   Using the original output filename instead would skip the already attempted
   texts, including the recorded failure. Temperature and seed are fixed, but
   results may differ across inference-library versions and hardware.
3. Compare the rerun with the saved translations before deciding whether to use
   it in the analysis. The main analysis continues to use the original file.

## Optional terminology annotation

`python scripts/swiss_conventions.py --french` regenerates the convention counts
and creates a review sheet if none exists. Existing sheets are preserved.
After annotating `results/terminology_review_french.csv`, run the same command
with `--summarise`. The report's automatic terminology table is produced
separately by `scripts/terminology_check.py`.
