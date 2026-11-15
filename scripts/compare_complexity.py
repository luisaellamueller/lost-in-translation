import json
import re
from statistics import mean
from importlib.metadata import version
from pathlib import Path
from typing import Any

import spacy
from wordfreq import zipf_frequency
from spacy.language import Language
from spacy.symbols import ORTH
from spacy.tokens import Doc


@Language.component("paragraph_boundaries")
def paragraph_boundaries(doc: Doc) -> Doc:
    """Start a new sentence at each nonempty source line.

    Args:
        doc: Tokenized text with punctuation-based sentence boundaries.

    Returns:
        Text with additional paragraph and list-item boundaries.
    """
    # Preserve paragraph and list boundaries before dependency parsing
    for i, token in enumerate(doc):
        if i and not token.is_space:
            previous = doc[i - 1]
            if "\n" in previous.text + previous.whitespace_:
                token.is_sent_start = True
    return doc


def measure_text(doc: Doc) -> dict[str, Any]:
    """Measure length and dependency structure of a parsed German text.

    Args:
        doc: German text processed by the trained spaCy parser.

    Returns:
        Document measures and sentence details for inspection.
    """
    # Measure sentences without counting punctuation or whitespace as words
    sentences = []
    distances = []
    for sentence in doc.sents:
        words = [token for token in sentence if not token.is_punct and not token.is_space]
        if not words:
            continue
        positions = {token.i: i for i, token in enumerate(words)}
        depth = max(sum(not ancestor.is_punct and not ancestor.is_space for ancestor in token.ancestors) for token in words)
        distances.extend(
            abs(positions[token.i] - positions[token.head.i])
            for token in words if token.head.i in positions and token.head != token
        )
        sentences.append({"text": sentence.text, "words": len(words), "tree_depth": depth})

    # Measure vocabulary using alphabetic tokens and fixed-size windows
    lexical_words = [token for token in doc if token.is_alpha]
    lemmas = [token.lemma_.lower() for token in lexical_words]
    mattr = {
        f"mattr_{window}": mean(
            len(set(lemmas[i:i + window])) / window
            for i in range(len(lemmas) - window + 1)
        ) if len(lemmas) >= window else None
        for window in [25, 50]
    }
    lexical_density = 100 * sum(
        token.pos_ in {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}
        for token in lexical_words
    ) / len(lexical_words)
    long_word_percent = 100 * sum(len(token.text) > 6 for token in lexical_words) / len(lexical_words)

    # Compare vocabulary frequency without treating missing entries as known rare words
    frequency_words = [
        {"text": token.text, "zipf": zipf_frequency(token.text, "de")}
        for token in lexical_words if token.pos_ in {"NOUN", "VERB", "ADJ", "ADV"}
    ]
    covered_frequencies = [word["zipf"] for word in frequency_words if word["zipf"] > 0]

    # Measure observable clause markers and base noun phrases
    subordinators = [token for token in doc if token.tag_ in {"KOUS", "KOUI"}]
    relatives = [token for token in doc if token.tag_ in {"PRELS", "PRELAT"}]
    noun_phrases = [
        {"text": chunk.text, "words": sum(token.is_alpha for token in chunk)}
        for chunk in doc.noun_chunks
        if chunk.root.pos_ in {"NOUN", "PROPN"}
    ]

    # Summarise separate features without creating a combined complexity score
    word_count = sum(sentence["words"] for sentence in sentences)
    return {
        "word_count": word_count,
        "sentence_count": len(sentences),
        "mean_sentence_words": word_count / len(sentences),
        "mean_sentence_tree_depth": sum(sentence["tree_depth"] for sentence in sentences) / len(sentences),
        "mean_dependency_distance": sum(distances) / len(distances) if distances else None,
        "mean_content_word_zipf": mean(word["zipf"] for word in frequency_words) if frequency_words else None,
        "mean_covered_content_word_zipf": mean(covered_frequencies) if covered_frequencies else None,
        "unlisted_content_word_percent": 100 * sum(word["zipf"] == 0 for word in frequency_words) / len(frequency_words) if frequency_words else None,
        "frequency_words": frequency_words,
        "alphabetic_word_count": len(lexical_words),
        "mean_word_characters": mean(len(token.text) for token in lexical_words),
        "long_word_percent": long_word_percent,
        "lexical_density_percent": lexical_density,
        **mattr,
        "subordinators_per_100_words": 100 * len(subordinators) / len(lexical_words),
        "relative_markers_per_100_words": 100 * len(relatives) / len(lexical_words),
        "mean_base_noun_phrase_words": mean(chunk["words"] for chunk in noun_phrases) if noun_phrases else None,
        "lix": len(lexical_words) / len(sentences) + long_word_percent,
        "noun_phrases": noun_phrases,
        "subordinators": [token.text for token in subordinators],
        "relative_markers": [token.text for token in relatives],
        "sentences": sentences,
    }


def load_parser(texts: list[str]) -> Language:
    """Load the shared German parser with the fixed sentence-boundary rules.

    Args:
        texts: Texts used to collect legal abbreviations.

    Returns:
        Configured German parsing pipeline.
    """
    nlp = spacy.load("de_core_news_sm", disable=["ner"])
    # Keep legal abbreviations together using the same rule for both versions
    abbreviations = {"Art.", "art."}
    for text in texts:
        abbreviations.update(re.findall(r"\b\d+[a-z]+\.", text))
    for abbreviation in sorted(abbreviations):
        nlp.tokenizer.add_special_case(abbreviation, [{ORTH: abbreviation}])
    nlp.add_pipe("sentencizer", before="parser", config={"punct_chars": [".", "!", "?"]})
    nlp.add_pipe("paragraph_boundaries", before="parser")
    return nlp


def compare_complexity(
    project_dir: Path,
    input_name: str = "complexity_translations.json",
    output_name: str = "complexity_multimeasure_pilot.json",
    completed_cases_only: bool = False,
) -> None:
    """Compare the fixed linguistic measures for complete translation pairs.

    Args:
        project_dir: Project directory containing the completed translations.
        input_name: Translation JSON filename in data/processed.
        output_name: Measurement JSON filename in data/processed.
        completed_cases_only: Explicitly exclude and report flagged generation failures.
    """
    # Load the fixed pilot and German parsing pipeline
    data_dir = project_dir / "data/processed"
    source = json.loads((data_dir / input_name).read_text(encoding="utf-8"))
    if source.get("failed_records") and not completed_cases_only:
        raise ValueError("Resolve flagged translations before evaluating the full sample.")
    nlp = load_parser([record[field] for record in source["records"] for field in ("reference_de", "translation_de")])
    records = []

    # Parse both complete German versions with identical settings
    for record in source["records"]:
        if record["finish_reason"] != "stop" or not record["translation_de"].strip():
            raise ValueError(f"Incomplete output in completed records: {record['document_id']}")
        official = measure_text(nlp(record["reference_de"]))
        generated = measure_text(nlp(record["translation_de"]))
        records.append({
            "document_id": record["document_id"],
            "title": record["title_de"],
            "official": official,
            "generated": generated,
        })

    # Summarise paired differences while giving each document equal weight
    summary = {}
    for metric, value in records[0]["official"].items():
        if value is not None and not isinstance(value, (int, float)):
            continue
        available = [record for record in records if record["official"][metric] is not None and record["generated"][metric] is not None]
        if not available:
            continue
        differences = [record["generated"][metric] - record["official"][metric] for record in available]
        summary[metric] = {
            "paired_count": len(available),
            "official_mean": mean(record["official"][metric] for record in available),
            "generated_mean": mean(record["generated"][metric] for record in available),
            "mean_difference": mean(differences),
            "generated_lower": sum(value < -1e-8 for value in differences),
            "generated_higher": sum(value > 1e-8 for value in differences),
            "ties": sum(abs(value) <= 1e-8 for value in differences),
        }

    # Save measurements and sentence boundaries for reproducible inspection
    output = {
        "input_file": input_name,
        "analysis_population": "Normally stopped outputs only; not necessarily semantically valid translations.",
        "attempted_count": len(source["records"]) + len(source.get("failed_records", [])),
        "completed_count": len(source["records"]),
        "completed_cases_only": completed_cases_only,
        "excluded_failures": [{"document_id": row["document_id"], "finish_reason": row["finish_reason"]} for row in source.get("failed_records", [])],
        "spacy_version": spacy.__version__,
        "parser": "de_core_news_sm",
        "parser_version": nlp.meta["version"],
        "wordfreq_version": version("wordfreq"),
        "definitions": {
            "sentences": "Punctuation sentencizer plus each nonempty line; preserve Art./art. and digit-letter legal references ending in a period as tokens. Semicolons do not split sentences. Identical rules for both versions.",
            "frequency": "Token-weighted surface-form Zipf frequency for alphabetic NOUN, VERB, ADJ, ADV tokens; exclude PROPN. Higher means more common. Report mean including zero, mean over positive entries only, and zero-entry percentage; zero means below resource coverage, not a validated difficulty score. Swiss spelling and domain vocabulary can affect coverage.",
            "lexical_measures": "Alphabetic tokens only. MATTR is mean lemma type-token ratio across overlapping windows of 25 or 50 words; unavailable below window size. Density counts NOUN, PROPN, VERB, ADJ, ADV as content words.",
            "clause_markers": "STTS KOUS/KOUI subordinators and PRELS/PRELAT relative markers per 100 alphabetic words. These are proxies, not counts of clauses or embedding depth.",
            "noun_phrases": "Mean alphabetic words per spaCy base noun chunk with NOUN/PROPN head; excludes pronominal chunks. Does not measure full nested noun phrases.",
            "lix": "Alphabetic words per sentence plus percentage of alphabetic words longer than six letters. Tokenization-specific implementation; no grade-level interpretation.",
            "words": "Tokens excluding punctuation and whitespace; numbers included.",
            "tree_depth": "Maximum number of non-punctuation, non-whitespace ancestors per sentence; root depth zero. Document value is the unweighted mean over sentences.",
            "dependency_distance": "Mean absolute word-position distance over non-root dependencies whose endpoints are word tokens; punctuation and whitespace excluded from positions.",
        },
        "limitations": "Sample provenance is recorded in the input and methods log. Parser estimates, not validated complexity judgments. Shortening can reflect omissions; length, syntax and tone are different constructs.",
        "unavailable": {"syllable_readability": "No German syllable resource installed; LIX used instead."},
        "summary": summary,
        "records": records,
    }
    path = data_dir / output_name
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {path}")


if __name__ == "__main__":
    # Run the structural diagnostic
    compare_complexity(Path(__file__).resolve().parents[1])
