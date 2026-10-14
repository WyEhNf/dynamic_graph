"""Model adapters provide genuine streaming timing and paired quality evidence."""
from dataclasses import dataclass
from typing import Protocol
import time


class StreamingModel(Protocol):
    def stream(self, context: str): ...


@dataclass
class ModelRun:
    output: str
    ttft_ms: float


def run_stream(model: StreamingModel, context: str) -> ModelRun:
    start = time.perf_counter_ns()
    first = None
    fragments = []
    for fragment in model.stream(context):
        # Empty keep-alive fragments are not first tokens.
        if fragment:
            if first is None:
                first = (time.perf_counter_ns() - start) / 1e6
            fragments.append(fragment)
    if first is None:
        raise ValueError("model stream produced no content")
    return ModelRun("".join(fragments), first)


def assess_pair(baseline: ModelRun, compressed: ModelRun,
                baseline_pass: bool, compressed_pass: bool) -> dict:
    return {"quality_gate_passed": compressed_pass and baseline_pass,
            "baseline_ttft_ms": baseline.ttft_ms,
            "compressed_ttft_ms": compressed.ttft_ms,
            "ttft_reduction": 1 - compressed.ttft_ms / baseline.ttft_ms
            if baseline.ttft_ms > 0 else None}
