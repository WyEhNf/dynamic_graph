"""Portfolio optimizer retaining only independently verified candidates."""
from time import perf_counter

from .model import BudgetExceeded, InfeasibleSchedule, InvalidBlock, VerificationFailed, parse_block
from .scheduler import schedule
from .incremental import schedule_incremental
from .search import search
from .verify import verify


def verified(data, candidate):
    try:
        return verify(data, candidate)
    except InvalidBlock as exc:
        raise VerificationFailed(f"Candidate was rejected by independent verifier: {exc}") from exc


def optimize(data, strategy="auto", time_budget_ms=100, max_states=30000, beam_width=128, memory_order="hazard"):
    started = perf_counter()
    if time_budget_ms <= 0 or max_states < 1 or beam_width < 1:
        raise ValueError("Search budgets and beam width must be positive")
    block = parse_block(data, memory_order)
    parse_ms = (perf_counter() - started) * 1000
    validation_ms = 0.0
    best, attempts = None, []
    if strategy == "auto":
        baselines = ("stable_fast", "pressure", "demand", "incremental") + (("ready", "stable") if len(block.instructions) <= 128 else ())
    else:
        baselines = ("ready", "stable") if strategy in ("beam", "exact") else (strategy,)
    deadline = started + time_budget_ms / 1000
    for baseline in baselines:
        remaining = (deadline - perf_counter()) * 1000
        if remaining <= 0:
            attempts.append({"strategy": baseline, "status": "time_budget_exhausted"})
            break
        try:
            if baseline in ("pressure", "demand", "incremental", "stable_fast"):
                candidate = schedule_incremental(block, policy=baseline, time_budget_ms=remaining)
            else:
                candidate = schedule(block, strategy=baseline, time_budget_ms=remaining)
            checked = perf_counter()
            verified(data, candidate)
            validation_ms += (perf_counter() - checked) * 1000
            attempts.append({"strategy": baseline, "status": "verified", "copies": candidate["stats"]["inserted_copy_count"]})
            if best is None or candidate["stats"]["inserted_copy_count"] < best["stats"]["inserted_copy_count"]:
                best = candidate
            if strategy == "auto" and best["stats"]["inserted_copy_count"] == 0:
                best["stats"]["search"] = {"outcome": "optimal_under_model", "explored_states": 0,
                                          "reason": "zero inserted COPY reaches the nonnegative lower bound",
                                          "memory_order": memory_order}
                break
        except (InfeasibleSchedule, BudgetExceeded) as exc:
            attempts.append({"strategy": baseline, "status": type(exc).__name__, "error": str(exc)})
    if strategy in ("auto", "beam", "exact") and not (strategy == "auto" and best and best["stats"]["inserted_copy_count"] == 0):
        remaining = (deadline - perf_counter()) * 1000
        # A retained incumbent makes large-graph search an optional quality
        # improvement. Bound that cost instead of consuming the whole budget.
        if strategy == "auto" and best and len(block.instructions) > 10:
            remaining = min(remaining, max(5.0, min(25.0, time_budget_ms * 0.2)))
        if remaining > 0:
            use_exact = strategy == "exact" or (strategy == "auto" and len(block.instructions) <= 10)
            try:
                candidate = search(block, best, time_budget_ms=remaining, max_states=max_states,
                                   beam_width=None if use_exact else beam_width)
                checked = perf_counter()
                verified(data, candidate)
                validation_ms += (perf_counter() - checked) * 1000
                best = candidate
                attempts.append({"strategy": "exact" if use_exact else "beam", "status": "verified",
                                 "search_outcome": candidate["stats"]["search"]["outcome"]})
            except (InfeasibleSchedule, BudgetExceeded) as exc:
                attempts.append({"strategy": "exact" if use_exact else "beam", "status": type(exc).__name__, "error": str(exc)})
        else:
            attempts.append({"strategy": "search", "status": "time_budget_exhausted"})
    if best is None:
        if any(a["status"] == "BudgetExceeded" or a["status"] == "time_budget_exhausted" for a in attempts):
            raise BudgetExceeded(f"No verified candidate within budget: {attempts}")
        raise InfeasibleSchedule(f"No verified candidate: {attempts}")
    best = {**best, "stats": {**best["stats"], "requested_strategy": strategy, "attempts": attempts,
                              "memory_order": memory_order,
                              "portfolio_elapsed_ms": (perf_counter() - started) * 1000,
                              "optimizer_parse_ms": parse_ms, "candidate_verify_ms": validation_ms,
                              "pure_schedule_ms": max(0.0, (perf_counter() - started) * 1000 - parse_ms - validation_ms)}}
    return best

