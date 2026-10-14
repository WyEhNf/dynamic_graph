"""Freeze two existing DEV tasks with synthetic irrelevant Python source.

CPU tokenizer and trusted reference checks only. Never constructs a model,
initializes CUDA, generates answers, or overwrites an existing fixture suite.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import shutil
import sys
import tempfile
import time

# Tokenizer-only Transformers usage; prevent optional torch/TF/Flax imports.
os.environ["USE_TORCH"] = "0"
os.environ["USE_TF"] = "0"
os.environ["USE_FLAX"] = "0"
os.environ["HF_HUB_OFFLINE"] = "1"
ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "adapters/research-v24"
FROZEN_MANIFEST_SHA = "9548ba0d5c8c1a3c7bb11ddf0c216b132b6990078b430d4636fd54cf50e2f5c2"
sys.path.insert(0, str(FROZEN))

from transformers import AutoTokenizer
from context_governance.bundles import digest_tree, load_case, source_chunks
from context_governance.core import govern, render
from context_governance.local_model import LocalModel, ModelTokenCounter
from context_governance.quality import check_code


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def relative_hashes(path):
    return {p.relative_to(path).as_posix(): sha(p)
            for p in sorted(path.rglob("*")) if p.is_file()}


def frozen_modules():
    manifest_path = FROZEN / "freeze-manifest.json"
    if sha(manifest_path) != FROZEN_MANIFEST_SHA:
        raise ValueError("v24 freeze manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    names = ("bundles.py", "core.py", "local_model.py", "quality.py")
    hashes = {}
    for name in names:
        relative = "context_governance/" + name
        actual = sha(FROZEN / relative)
        if actual != manifest["file_sha256"][relative]:
            raise ValueError("frozen v24 module changed: " + name)
        hashes[relative] = actual
    return hashes


def added_function(rng, index):
    # No imports, initialization calls or names related to either task.
    # Random hex documentation is deliberately synthetic contextual padding.
    annotation = " ".join(f"{rng.getrandbits(32):08x}" for _ in range(18))
    salt = rng.randrange(1000, 100000)
    return (f"def nebula_fragment_{index:04d}(payload):\n"
            f'    """Archival digest {annotation}."""\n'
            f"    return len(payload) + {salt}\n\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "fixtures/combined-public-v17")
    parser.add_argument("--output", type=Path, default=ROOT / "fixtures/long-engineering-v25")
    parser.add_argument("--model", type=Path, default=ROOT / "models/Qwen2.5-Coder-7B-Instruct")
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination.exists():
        raise ValueError("Frozen destination already exists; do not overwrite or retune it")
    started = time.perf_counter()
    started_unix = time.time()
    source = args.source.resolve()
    source_before = digest_tree(source)
    module_hashes = frozen_modules()
    model = args.model.resolve()
    lock = json.loads((model / "model-lock.json").read_text(encoding="utf-8"))
    token_files = ("config.json", "tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt")
    tokenizer_hashes = {name: sha(model / name) for name in token_files}
    if any(tokenizer_hashes[name] != lock["files"][name]["sha256"] for name in token_files):
        raise ValueError("Installed tokenizer/config differs from the immutable model lock")
    load_start = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True, trust_remote_code=False)
    tokenizer_load_seconds = time.perf_counter() - load_start
    # Access the frozen prompt method without running LocalModel.__init__.
    formatter = LocalModel.__new__(LocalModel)
    formatter.tokenizer = tokenizer
    formatter.prompt_policy = "concise-v3"
    counter = ModelTokenCounter(tokenizer)
    config = json.loads((model / "config.json").read_text(encoding="utf-8"))
    if config["max_position_embeddings"] != 32768:
        raise ValueError("Model position limit differs from the declared experiment")
    def prompt_count(prompt):
        # Exactly the tokenizer invocation used by LocalModel.generate,
        # including the complete rendered chat template and default special tokens.
        return len(tokenizer(prompt, truncation=False)["input_ids"])

    records = []
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="long-engineering-v25-staging-", dir=destination.parent) as temporary:
        suite = Path(temporary) / "suite"
        suite.mkdir()
        for folder in ("metadata", "spec", "tests", "oracle", "repo_bundles"):
            (suite / folder).mkdir()
        if (source / "templates").exists():
            shutil.copytree(source / "templates", suite / "templates")
        for case_index, case_id in enumerate(("clamp", "allocate_round_robin")):
            case_start = time.perf_counter()
            original_meta, original_root, spec, original_items = load_case(source, case_id)
            original_hashes = relative_hashes(original_root)
            copied_hashes = {}
            for folder, suffix in (("metadata", ".json"), ("spec", ".md"), ("tests", ".py"), ("oracle", ".py")):
                original = source / folder / (case_id + suffix)
                copied_hashes[folder] = sha(original)
                shutil.copy2(original, suite / folder / original.name)
            bundle = suite / "repo_bundles" / original_meta["baseline_bundle"]
            shutil.copytree(original_root, bundle)
            seed = 252500 + case_index
            rng = random.Random(seed)
            function_count = 0
            additions = {}
            history = [x for x in original_items if x.id.startswith("history-")]
            before_history = [x for x in original_items if not x.id.startswith("history-")]
            sizing_start = time.perf_counter()
            while True:
                filename = f"zz_v25_archive_{function_count // 12:03d}.py"
                additions[filename] = additions.get(filename, "") + added_function(rng, function_count)
                function_count += 1
                chunks = [chunk for name, text in sorted(additions.items())
                          for chunk in source_chunks(name, text)]
                candidate = before_history + chunks + history
                prompt = formatter.prompt(render(candidate), spec)
                count = prompt_count(prompt)
                if count >= 31000:
                    if count > 31500:
                        raise ValueError("Deterministic complete-function increment overshot the declared range")
                    break
                if function_count > 1000:
                    raise ValueError("Synthetic padding construction exceeded its predeclared bound")
            sizing_seconds = time.perf_counter() - sizing_start
            for name, text in additions.items():
                ast.parse(text)
                (bundle / name).write_text(text, encoding="utf-8", newline="\n")
            meta = dict(original_meta)
            meta["snapshot_sha256"] = digest_tree(bundle)
            meta["split"] = "Existing DEV task with synthetic long-context extension; not a new holdout"
            meta["long_context_extension"] = {"version": 25, "seed": seed,
                "added_modules": len(additions), "added_functions": function_count,
                "original_snapshot_sha256": original_meta["snapshot_sha256"]}
            write_json(suite / "metadata" / (case_id + ".json"), meta)
            checked_meta, _, copied_spec, items = load_case(suite, case_id)
            if spec != copied_spec or render(items) != render(candidate):
                raise AssertionError("Persisted bundle differs from the token-sized prompt")
            if any(sha(bundle / name) != digest for name, digest in original_hashes.items()):
                raise AssertionError("An existing source file was modified")
            full_prompt = formatter.prompt(render(items), spec)
            if prompt_count(full_prompt) != count or count + 512 > 32768:
                raise AssertionError("Actual chat prompt violates the model window")
            govern_start = time.perf_counter()
            selection = govern(spec, items, 650, counter, checked_meta["context_dependencies"])
            govern_seconds = time.perf_counter() - govern_start
            comp_prompt = formatter.prompt(selection["context"], spec)
            comp_count = prompt_count(comp_prompt)
            if comp_count + 512 > 32768 or selection["metrics"]["output_units"] > 650:
                raise AssertionError("Compressed prompt exceeds budget/window")
            selected_sources = {}
            for item in selection["selected"]:
                if item["kind"] == "code":
                    selected_sources.setdefault(item["id"].split(":")[0], []).append(item["text"])
            check_start = time.perf_counter()
            oracle = (suite / "oracle" / (case_id + ".py")).read_text(encoding="utf-8")
            placeholder = (bundle / meta["target_file"]).read_text(encoding="utf-8")
            test = suite / "tests" / (case_id + ".py")
            checks = {"full_reference": check_code(oracle, bundle, meta["target_file"], test),
                      "full_placeholder": check_code(placeholder, bundle, meta["target_file"], test)}
            with tempfile.TemporaryDirectory(prefix="v25-selected-") as selected_directory:
                selected_root = Path(selected_directory)
                for name, pieces in selected_sources.items():
                    path = selected_root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("".join(pieces), encoding="utf-8", newline="\n")
                checks["selected_reference"] = check_code(oracle, selected_root, meta["target_file"], test)
                checks["selected_placeholder"] = check_code(placeholder, selected_root, meta["target_file"], test)
            if not all(checks[key]["passed"] for key in ("full_reference", "selected_reference")):
                raise AssertionError("Reference implementation failed a CPU functional check")
            if any(checks[key]["passed"] for key in ("full_placeholder", "selected_placeholder")):
                raise AssertionError("Placeholder was incorrectly accepted")
            original_dependencies = original_meta["context_dependencies"]
            if any(checked_meta["context_dependencies"].get(key) != dependencies
                   for key, dependencies in original_dependencies.items()):
                raise AssertionError("Original dependency edges were changed")
            record = {"id": case_id, "seed": seed,
                "origin_snapshot_sha256": original_meta["snapshot_sha256"],
                "origin_source_sha256": original_hashes, "origin_component_sha256": copied_hashes,
                "snapshot_sha256": meta["snapshot_sha256"],
                "added_module_count": len(additions), "added_function_count": function_count,
                "added_sources": [{"path": name, "sha256": sha(bundle / name),
                    "complete_source": text,
                    "function_count": sum(isinstance(node, ast.FunctionDef) for node in ast.parse(text).body)}
                    for name, text in sorted(additions.items())],
                "full_prompt_tokens": count, "compressed_prompt_tokens": comp_count,
                "compressed_context_tokens": selection["metrics"]["output_units"],
                "baseline_prompt_sha256": hashlib.sha256(full_prompt.encode()).hexdigest(),
                "compressed_prompt_sha256": hashlib.sha256(comp_prompt.encode()).hexdigest(),
                "selected_code_ids": [x["id"] for x in selection["selected"] if x["kind"] == "code"],
                "selected_modules": sorted(selected_sources),
                "original_dependency_map": original_dependencies,
                "governance_metrics": selection["metrics"], "functional_checks": checks,
                "preparation_seconds": time.perf_counter() - case_start,
                "sizing_seconds": sizing_seconds, "governance_seconds": govern_seconds,
                "functional_checks_seconds": time.perf_counter() - check_start}
            records.append(record)
            print(json.dumps({"case": case_id, "full_tokens": count,
                              "compressed_tokens": comp_count, "added_functions": function_count}), flush=True)
        if digest_tree(source) != source_before:
            raise AssertionError("Historical source suite changed during preparation")
        if "torch" in sys.modules:
            raise AssertionError("Tokenizer-only preparation unexpectedly imported torch")
        provenance = {"version": 25, "origin": "Existing DEV tasks plus deterministic irrelevant Python files",
            "scope": "Synthetic long engineering extensions of known DEV tasks, not new holdouts or model quality evidence",
            "source_suite": str(source), "source_suite_sha256": source_before,
            "source_manifest_sha256": sha(source / "manifest.json"),
            "script_sha256": sha(__file__), "started_unix": started_unix,
            "v24_freeze_manifest_sha256": FROZEN_MANIFEST_SHA, "v24_module_sha256": module_hashes,
            "model_tokenizer": str(model), "model_lock_sha256": sha(model / "model-lock.json"),
            "tokenizer_file_sha256": tokenizer_hashes, "chat_template_sha256": hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),
            "prompt_policy": "concise-v3", "budget_context_tokens": 650,
            "input_prompt_target_tokens": [31000, 31500], "max_new_tokens": 512,
            "model_position_limit": 32768, "no_input_truncation": True,
            "tokenizer_load_seconds": tokenizer_load_seconds,
            "preparation_seconds": time.perf_counter() - started,
            "python": platform.python_version(), "no_gpu_used": True, "torch_imported": False,
            "model_generation_calls": 0, "cases": records,
            "predeclared_model_followup": {"repeats": 1, "timed_calls": 4,
                "stages": "single", "modes": ["baseline", "compressed"],
                "model": "Qwen2.5-Coder-7B-Instruct", "weight_quantization": "nf4",
                "kv_cache_policy": "reclaimed", "kv_offload_min_tokens": 16384,
                "prefill_chunk_tokens": 1024, "max_new_tokens": 512,
                "order": {"clamp": ["baseline", "compressed"],
                          "allocate_round_robin": ["compressed", "baseline"]},
                "scope": "One pair per known DEV task; no repeat stability or independent holdout claim"}}
        write_json(suite / "provenance.json", provenance)
        manifest = {"version": 25, "case_ids": [x["id"] for x in records],
            "scope": provenance["scope"], "constructed_unix": time.time(),
            "script_sha256": sha(__file__), "provenance_sha256": sha(suite / "provenance.json"),
            "frozen_parameters": {k: provenance[k] for k in ("input_prompt_target_tokens", "max_new_tokens",
                "model_position_limit", "budget_context_tokens", "prompt_policy", "predeclared_model_followup")},
            "file_sha256": relative_hashes(suite)}
        write_json(suite / "manifest.json", manifest)
        # Publish only after every size, source-preservation and CPU check succeeds.
        suite.rename(destination)
    print(json.dumps({"output": str(destination), "manifest_sha256": sha(destination / "manifest.json"),
                      "preparation_seconds": time.perf_counter() - started,
                      "model_generation_calls": 0, "no_gpu_used": True}), flush=True)


if __name__ == "__main__":
    main()
