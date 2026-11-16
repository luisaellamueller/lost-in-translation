#!/usr/bin/env bash
# Recompute every number, table and figure in the report from the data in this repository.
# Run from the repository root with the virtual environment activated:
#     bash reproduce.sh            # everything offline, from the committed data
#     bash reproduce.sh --fetch    # also re-download the author data from the Parliament API
# The machine translations themselves are not regenerated here (needs the 2.5 GB model,
# about 2 hours); see docs/french_sample_howto.md. See docs/report_numbers.md for which
# output file holds which number.
set -euo pipefail

echo "== 1. Corpus: 10,573 pairs, 41 exclusions, consistency checks"
python scripts/check_data.py

echo "== 2. Author language of every motion (French-authored list, biography check)"
python scripts/author_language_corpus.py "$@"

echo "== 3. The 260-motion French-authored sample follows from the rule and seed"
python scripts/prepare_french_sample.py --check

echo "== 4. RQ1 complexity measures (spaCy) and Figure 2"
python scripts/compare_expanded.py --french
python scripts/report_rq1.py

echo "== 5. RQ2 Swiss conventions, terminology (Table 1), screening"
python scripts/swiss_conventions.py --french
python scripts/terminology_check.py
python scripts/screen_translations.py

echo "== 6. RQ3 similarity over time (Figure 3) and special characters (Table 2)"
python scripts/similarity_over_time.py
python scripts/special_characters.py

echo "== 7. Appendix A"
python scripts/historical_summary.py

echo "Done. Results in results/, figures in docs/figures/."
