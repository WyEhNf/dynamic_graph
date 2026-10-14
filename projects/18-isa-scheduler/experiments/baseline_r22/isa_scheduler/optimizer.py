"""Portfolio optimizer retaining only independently verified candidates."""
from time import perf_counter
from collections import Counter

from .model import BudgetExceeded, InfeasibleSchedule, InvalidBlock, VerificationFailed, parse_block
from .bounds import forest_capacity_bound
from .spine_bounds import spine_capacity_bound
from .scheduler import schedule
from .incremental import schedule_incremental, PreparedGraph
from .forest_linear import emit_forest,eligible as forest_eligible
from .search import search
from .verify import verify, VerificationContext


def verified(data, candidate, context=None):
    try:
        return context.check(candidate) if context is not None else verify(data, candidate)
    except InvalidBlock as exc:
        raise VerificationFailed(f"Candidate was rejected by independent verifier: {exc}") from exc


def original_candidate(block, remaining_ms):
    """A legal original ordering already attains the zero-insertion lower bound."""
    tick = perf_counter()
    deadline = tick + remaining_ms / 1000
    output = []
    for node in block.instructions:
        if node.index % 128 == 0 and perf_counter() >= deadline:
            raise BudgetExceeded("Original-order export budget exhausted")
        row = {"id": node.index, "op": node.op}
        if node.reg is not None:
            row["reg"] = node.reg
        tokens = [f"t#{node.index-source}" for source in node.args]
        if node.op == "COPY":
            row["source"] = tokens[0]
        elif tokens:
            row["inputs"] = tokens
        output.append(row)
    count = len(output)
    copies = sum(row["op"] == "COPY" for row in output)
    return {"block_id": block.block_id, "optimized_instructions": output, "stats": {
        "strategy": "original", "original_instruction_count": count,
        "optimized_instruction_count": count, "inserted_copy_count": 0,
        "total_copy_count": copies, "copy_ratio_output": copies/count if count else 0.0,
        "inserted_copy_ratio_original": 0.0, "elapsed_ms": (perf_counter()-tick)*1000,
        "original_order": list(range(count)),
        "bit_width": block.bit_width, "max_back_distance": block.window}}


def optimize(data, strategy="auto", time_budget_ms=100, max_states=30000, beam_width=128, memory_order="hazard"):
    started = perf_counter()
    if time_budget_ms <= 0 or max_states < 1 or beam_width < 1:
        raise ValueError("Search budgets and beam width must be positive")
    block = parse_block(data, memory_order)
    certificate = None
    if strategy in ("auto", "exact"):
        certificate = forest_capacity_bound(block)
        if certificate and certificate["infeasible_under_model"]:
            raise InfeasibleSchedule(f"proven_infeasible_under_model: {certificate}")
        if sum(node.op=="GET" for node in block.instructions)>=block.window:
            spine_certificate=spine_capacity_bound(block)
            if spine_certificate and spine_certificate["infeasible_under_model"]:
                raise InfeasibleSchedule(f"proven_infeasible_under_model: {spine_certificate}")
    parse_ms = (perf_counter() - started) * 1000
    validation_ms = 0.0
    context = None  # Construct only after the first viable candidate exists.
    prepared = None
    best, attempts = None, []
    if strategy == "auto":
        legal_original = all(node.index-source <= block.window for node in block.instructions for source in node.args)
        baselines = ("original",) if legal_original else ("stable_fast", "pressure", "ready_fast", "demand", "incremental")
        if not legal_original and certificate and certificate["unequal_work_equal_demand_pairs"]:
            # Work tie-break is reliable only as a forest heuristic. Keep every
            # earlier baseline; finite budget may still prevent reaching one.
            baselines=("stable_fast","size_pressure","pressure","ready_fast","demand","incremental")
        if not legal_original and sum(node.op == "SET" for node in block.instructions) > 1:
            get_uses = Counter(source for node in block.instructions for source in set(node.args)
                               if block.instructions[source].op == "GET")
            # More than one heavily shared input and multiple outputs is a
            # structural opportunity to finish one input's consumers together.
            # No generator family names or seed-specific rules are used.
            if sum(uses >= 4 for uses in get_uses.values()) > 1:
                baselines = ("affinity", "stable_fast", "pressure", "ready_fast", "demand", "incremental")
    else:
        baselines = ("ready", "stable") if strategy in ("beam", "exact") else (strategy,)
    deadline = started + time_budget_ms / 1000
    for baseline in baselines:
        remaining = (deadline - perf_counter()) * 1000
        if remaining <= 0:
            attempts.append({"strategy": baseline, "status": "time_budget_exhausted"})
            break
        try:
            if baseline == "original":
                candidate = original_candidate(block, remaining)
            elif baseline in ("pressure", "demand", "incremental", "stable_fast", "ready_fast", "affinity", "deadline", "age_first", "size_pressure", "forest_work"):
                if strategy == "auto" and baseline in ("affinity","size_pressure") and best is None:
                    remaining = min(remaining, max(25.0, time_budget_ms * 0.6))
                prep_started = perf_counter()
                if prepared is None:
                    prepared = PreparedGraph(block,time_budget_ms=remaining)
                if strategy == "auto" and baseline == "stable_fast" and prepared.original_peak_live > block.window:
                    attempts.append({"strategy": baseline, "status": "skipped_original_order_capacity",
                                     "peak_live": prepared.original_peak_live, "window": block.window,
                                     "scope": "fixed original order only; not whole-problem infeasibility"})
                    continue
                remaining -= (perf_counter()-prep_started)*1000
                if baseline in ("size_pressure","forest_work") and forest_eligible(block,prepared):
                    candidate=emit_forest(block,prepared,time_budget_ms=remaining,work_first=baseline=="forest_work")
                elif baseline=="forest_work":
                    raise InfeasibleSchedule("forest_work requires complete unshared GET/SET forests")
                else:
                    candidate = schedule_incremental(block, policy=baseline, time_budget_ms=remaining,prepared=prepared)
            else:
                candidate = schedule(block, strategy=baseline, time_budget_ms=remaining)
            if best is not None and candidate["stats"]["inserted_copy_count"] >= best["stats"]["inserted_copy_count"]:
                attempts.append({"strategy": baseline, "status": "discarded_no_improvement_unverified",
                                 "copies": candidate["stats"]["inserted_copy_count"]})
                continue
            checked = perf_counter()
            if context is None:
                context = VerificationContext(data)
            verified(data, candidate, context)
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
                promoted = best is None or candidate["stats"]["inserted_copy_count"] < best["stats"]["inserted_copy_count"]
                if promoted:
                    if context is None:
                        context = VerificationContext(data)
                    verified(data, candidate, context)
                    validation_ms += (perf_counter() - checked) * 1000
                    best = candidate
                elif "search" in candidate["stats"]:
                    best = {**best, "stats": {**best["stats"], "search": candidate["stats"]["search"]}}
                attempts.append({"strategy": "exact" if use_exact else "beam", "status": "verified" if promoted else "retained_verified_incumbent",
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

