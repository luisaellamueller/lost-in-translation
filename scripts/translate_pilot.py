import json
from pathlib import Path
from time import perf_counter

from jinja2.sandbox import ImmutableSandboxedEnvironment
from llama_cpp import Llama


def translate_pilot(
    project_dir: Path,
    input_name: str = "pilot_pairs.json",
    output_name: str = "pilot_translations.json",
    record_over_limit: bool = False,
) -> None:
    """Translate the French pilot texts using the GGUF's embedded template.

    Args:
        project_dir: Project directory containing the model and pilot data.
        input_name: Input JSON filename in data/processed.
        output_name: Output JSON filename in data/processed.
        record_over_limit: If True, a document whose prompt exceeds the 2048-token
            input limit is saved as a failed attempt (finish_reason
            "input_over_limit") instead of stopping the run. Default False keeps
            the original behaviour.
    """
    # Load the pilot and local translation model
    data = json.loads((project_dir / "data/processed" / input_name).read_text(encoding="utf-8"))
    model_path = project_dir / "models/translategemma-4b-it-Q4_K_M.gguf"
    output_path = project_dir / "data/processed" / output_name
    output = {
        "model_file": model_path.name,
        "settings": {"temperature": 0.0, "max_tokens": 1800, "n_ctx": 4096, "seed": 42, "repeat_penalty": 1.0},
        "source_language": "fr",
        "target_language": "de",
        "records": [],
        "failed_records": [],
    }

    # Resume only completed records from the same inputs and settings
    if output_path.exists():
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        for key in ("model_file", "settings", "source_language", "target_language"):
            if saved[key] != output[key]:
                raise ValueError(f"Saved {key} differs; use a separate output file.")
        inputs = {record["document_id"]: record for record in data["records"]}
        for record in saved["records"] + saved.get("failed_records", []):
            original = inputs[record["document_id"]]
            if any(record[key] != value for key, value in original.items()):
                raise ValueError(f"Input changed for {record['document_id']}.")
        for record in saved["records"]:
            if record["finish_reason"] != "stop" or not record["translation_de"]:
                raise ValueError(f"Inspect incomplete document {record['document_id']} before resuming.")
        saved.setdefault("failed_records", [])
        output = saved
    processed = {record["document_id"] for record in output["records"] + output["failed_records"]}
    pending = [record for record in data["records"] if record["document_id"] not in processed]
    if not pending:
        print(f"No unattempted documents: {len(output['records'])} completed, {len(output['failed_records'])} failed; inspect failures before evaluation.")
        return
    model = Llama(model_path=str(model_path), n_ctx=4096, n_gpu_layers=-1, seed=42, verbose=False)
    template = ImmutableSandboxedEnvironment().from_string(model.metadata["tokenizer.chat_template"])

    # Render the model's own translation prompt for each full text
    for record in pending:
        messages = [{"role": "user", "content": [{
            "type": "text", "source_lang_code": "fr", "target_lang_code": "de", "text": record["input_fr"],
        }]}]
        prompt = template.render(messages=messages, bos_token="<bos>", add_generation_prompt=True)
        tokens = model.tokenize(prompt.encode("utf-8"), add_bos=False, special=True)
        if len(tokens) > 2048:
            if not record_over_limit:
                raise ValueError(f"Document {record['document_id']} exceeds the pilot's 2048-token input limit.")
            # Keep the fixed sample: record the document as a failure, never truncate or redraw
            output["failed_records"].append({**record, "translation_de": "", "prompt": prompt,
                                             "finish_reason": "input_over_limit",
                                             "usage": {"prompt_tokens": len(tokens)}, "generation_seconds": 0.0})
            temporary_path = output_path.with_suffix(".tmp")
            temporary_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary_path.replace(output_path)
            print(f"Flagged over input limit ({len(tokens)} tokens): {record['document_id']}", flush=True)
            continue

        # Generate without showing the model the German reference
        print(f"Translating {record['document_id']}...", flush=True)
        start = perf_counter()
        response = model.create_completion(
            prompt=tokens, temperature=0.0, max_tokens=1800,
            repeat_penalty=1.0, stop=["<end_of_turn>", "<eos>"],
        )
        choice = response["choices"][0]
        result = {
            **record,
            "translation_de": choice["text"].strip(),
            "prompt": prompt,
            "finish_reason": choice["finish_reason"],
            "usage": response["usage"],
            "generation_seconds": perf_counter() - start,
        }
        failed = choice["finish_reason"] != "stop" or not result["translation_de"]
        destination = "failed_records" if failed else "records"
        output[destination].append(result)

        # Save every attempt and keep failed outputs separate for inspection
        temporary_path = output_path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary_path.replace(output_path)
        status = "Flagged incomplete" if failed else "Saved"
        print(f"{status}: {record['document_id']}", flush=True)

    print(f"Finished attempts: {len(output['records'])} completed, {len(output['failed_records'])} failed. {output_path}")


if __name__ == "__main__":
    # Translate the development pilot
    translate_pilot(Path(__file__).resolve().parents[1])
