# Isolated v24 KV policy integration

This directory freezes all 25 v22 modules in `baseline-source/` and contains a separate full candidate package in `context_governance/`. Only `local_model.py`, `public_examples.py` and `run_local_eval.py` differ. Active `src/`, v22, other adapters and reports are untouched.

Constructor additions:

- `kv_cache_policy='resident'`: original resident cache behavior, including chunked prefill. Optional `offloaded` selects Transformers offloading; `reclaimed` additionally synchronizes and returns unused CUDA allocator blocks after each explicit prefill chunk.
- `kv_offload_min_tokens=16384`: nonnegative integer. Offloading requires CUDA, a nonresident policy, and **input tokens strictly greater than** this threshold. Nonresident policies reject CPU even for below-threshold prompts. `cuda:1` is supported via device type resolution.
- Chunked prefill uses `DynamicCache(config=..., offloading=offload)`. All earlier prompt tokens remain cached; the final nonempty prompt chunk is processed by `generate` with the original full encoded input.
- Nonchunked eligible prompts use `cache_implementation='offloaded'`. They perform no explicit allocator reclamation. Decode is unchanged. Resident/offloaded policies never call `empty_cache`.

CLI additions are `--kv-cache-policy {resident,offloaded,reclaimed}` and `--kv-offload-min-tokens INTEGER`. Both values are recorded in the evaluation report. Defaults keep single generation, resident cache and literal-v17 protocol. The public-contract-v22 prompt and literal protocol remain; v24 additionally rejects Python-keyword target module path components (for example `class.py`) before constructing the trusted import template. The other 22 modules are byte-for-byte preserved from the baseline.

The standalone `generate_candidate.py` refuses an existing candidate destination. In a fresh copy with the sibling v22 package and v23 resource reference, it reproduces all 25 candidate source files byte-for-byte. `provenance.json` records each baseline/candidate source SHA and the generator/resource-reference hashes. `freeze-manifest.json` also freezes scripts and tests.

CPU-only tests: run `python -B -m unittest discover -s adapters/research-v24 -p test_kv_policy.py -v` with the project core Python environment. They mock torch, Transformers, tensor slicing, model calls and cache objects; no model dependency or GPU is used. Eleven tests cover configuration rejection, 96 policy/shape/device combinations, strict threshold boundaries (including 16384/16385), zero threshold, synchronized reclamation ordering, final output token counts, full input token consumption, repeated request cache isolation, context overflow, all-module freezing, exact prompt compatibility, generator replay, CLI wiring/default/report fields, and rejection of keyword module paths before checker execution.

`test-results-initial-failed.json` retains the initial harness/development failure. An intermediate local editing step read UTF-8 with the Windows default encoding and damaged two regex character classes; the candidate was regenerated from the frozen baseline using explicit UTF-8, then every generated file was checked for exact replay. The threshold-zero fixture also originally requested a chunk larger than the input while expecting a cache object; that assertion setup was corrected. Final `test-results.json` contains the successful run. No runtime result or GPU observation was obtained during either run.

These tests provide configuration and lifecycle evidence only. The separate v23 long-input token-ID/performance observations are **not v24 measurements**, and this candidate makes no GPU performance, memory-saving or model-quality claim. Parent integration must run its own GPU compatibility/quality verification before promotion.

The original four literal-v17 tests plus six frozen public-contract-v22 tests also ran against the v24 module imports: 10/10 passed, 13.449 seconds, in `public-compatibility-results.json`. This remains CPU protocol/execution evidence only.
