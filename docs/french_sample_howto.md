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

## Steps (from the repository root, with `.venv` activated)

1. One-time setup for translation (see README, "Optional: run the local translator"):
   ```bash
   pip install -r requirements-translation.txt
   mkdir -p models
   # download translategemma-4b-it-Q4_K_M.gguf into models/, then check:
   shasum -a 256 models/translategemma-4b-it-Q4_K_M.gguf
   # must be e7d9523174272fca61264b339f06d10c6115426267bb0f752b0124084e487b8e
   ```
2. Translate the 197 new texts (resumes if interrupted; about 1–2 hours):
   ```bash
   python - <<'PYCODE'
   from pathlib import Path
   from scripts.translate_pilot import translate_pilot
   translate_pilot(Path("."),
       input_name="complexity_fr_author_pairs.json",
       output_name="complexity_fr_author_translations.json",
       record_over_limit=True)
   PYCODE
   ```
   One text (20003342, about 8,900 characters) is expected to exceed the
   2,048-token input limit. It is recorded as a failure (`input_over_limit`),
   following the project rule: never truncate or redraw.
3. Compare (same measures and bootstrap as the main analysis):
   ```bash
   python scripts/compare_expanded.py --french
   ```
   This writes `data/processed/complexity_fr_author_results.json` and `docs/french_author_comparison.md`.
4. Swiss conventions and the terminology review sheet:
   ```bash
   python scripts/swiss_conventions.py --french
   # annotate results/terminology_review_french.csv, then:
   python scripts/swiss_conventions.py --french --summarise
   ```
5. Commit the new outputs. Never overwrite Klara's original files.
