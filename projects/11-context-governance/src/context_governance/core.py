from dataclasses import dataclass, asdict
import re
import time
from typing import Protocol


class TokenCounter(Protocol):
    name: str
    def count(self, text: str) -> int: ...


class ByteEstimate:
    """Conservative budget units, NOT the model's token count."""
    name = "utf8-bytes-budget-estimate"
    def count(self, text: str) -> int:
        return len(text.encode("utf-8"))


@dataclass(frozen=True)
class Item:
    id: str
    kind: str
    text: str
    protected: bool = False
    utility: float = 0.0


def terms(text: str) -> set[str]:
    words = set(re.findall(r"[a-zA-Z_][\w.]*|[\u4e00-\u9fff]", text))
    result = {word.lower() for word in words}
    # Preserve complete names while allowing parser_value / ParserValue and
    # package.parser to match a task mentioning the underlying concept.
    for word in words:
        if '_' in word or '.' in word or (len(word)>1 and not word.islower()):
            split = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', word)
            result.update(part.lower() for part in re.split(r'[_.\s]+',split) if part)
    return result


def query_terms(task: str) -> set[str]:
    # Generic task language should not make every unrelated function relevant.
    return terms(task) - {'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'for',
                         'is', 'are', 'its', 'with', 'from', 'by', 'as', 'be',
                         'return', 'implement', 'function', 'file', 'target',
                         'complete', 'content', 'current', 'task', 'values',
                         'input', 'output', 'existing', 'dependencies', 'must',
                         'stay', 'available', 'do', 'not', 'it', 'all',
                         'py', 'python', 'md', 'txt', 'json', 'source', 'code'}


def render(items: list[Item]) -> str:
    # Account for labels and separators in the budget as well as payload.
    return "\n\n".join(f"[{x.kind}:{x.id}]\n{x.text}" for x in items)


class PreparedContext:
    """Request-session cache owned by the caller, never a global text cache.

    Rebuild after a source/dependency change. Fragment costs only screen
    candidates; accepted contexts are always recounted with the live counter.
    A different counter instance invalidates costs. Clear costs if the caller
    changes a tokenizer's configuration in place.
    """
    def __init__(self, items, dependencies=None):
        self.items = tuple(items)
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError('context IDs must be unique')
        self.dependencies = {key: tuple(value) for key,value in (dependencies or {}).items()}
        self.term_sets = {item.id: frozenset(terms(item.text + ' ' + item.id))
                          for item in self.items if not item.protected}
        self.closures = {}
        self._counter = None
        self.costs = {}

    def validate(self, items, dependencies):
        if tuple(items) != self.items or {k:tuple(v) for k,v in dependencies.items()} != self.dependencies:
            raise ValueError('prepared context is stale; rebuild after changing source or dependencies')

    def clear_costs(self):
        self.costs.clear()
        self._counter = None

    def revised(self, items, dependencies=None):
        """Create a new snapshot index, reusing only exactly unchanged items.

        The old snapshot remains immutable. Cost dictionaries are copied,
        never shared; closure caches are retained only for identical graph
        structure and node IDs. Live acceptance still uses exact counting.
        """
        updated = tuple(items)
        lookup = {item.id: item for item in updated}
        if len(lookup) != len(updated):
            raise ValueError('context IDs must be unique')
        graph = {key: tuple(value) for key, value in (dependencies or {}).items()}
        if any(key not in lookup or any(node not in lookup for node in values)
               for key, values in graph.items()):
            raise ValueError('dependency map contains unknown context IDs')
        previous = {item.id: item for item in self.items}
        unchanged = {item.id for item in updated if previous.get(item.id) == item}
        result = PreparedContext.__new__(PreparedContext)
        result.items = updated
        result.dependencies = graph
        result.term_sets = {
            item.id: self.term_sets[item.id] if item.id in unchanged
            else frozenset(terms(item.text + ' ' + item.id))
            for item in updated if not item.protected}
        result.closures = (self.closures.copy()
                           if graph == self.dependencies and set(lookup) == set(previous) else {})
        result._counter = self._counter
        result.costs = {key: value for key, value in self.costs.items() if key in unchanged}
        return result


def analyze_importance(task: str, items: list[Item], prepared=None):
    """Semantic lexical relevance + observed utility + novelty; stable ties."""
    start = time.perf_counter_ns()
    query = query_terms(task)
    candidates = []
    seen = set()
    for order, item in enumerate(items):
        if item.protected:
            continue
        item_terms = prepared.term_sets[item.id] if prepared else terms(item.text + ' ' + item.id)
        overlap = len(query & item_terms) / max(1, len(query))
        score = overlap + max(0.0, min(1.0, item.utility))
        identity = (item.kind, item.text)
        if item.kind in {'memory', 'tool'} and identity in seen:
            score -= 1.0
        seen.add(identity)
        candidates.append((-score, order, item))
    return candidates, (time.perf_counter_ns()-start)/1e6


def govern(task: str, items: list[Item], budget: int,
           counter: TokenCounter | None = None, dependencies: dict[str, list[str]] | None = None,
           measure_input: bool = True, prepared: PreparedContext | None = None) -> dict:
    if budget < 1:
        raise ValueError("budget must be positive")
    if len({x.id for x in items}) != len(items):
        raise ValueError("context IDs must be unique")
    counter = counter or ByteEstimate()
    dependencies = dependencies or {}
    if prepared: prepared.validate(items, dependencies)
    lookup = {item.id:item for item in items}
    if any(key not in lookup or any(x not in lookup for x in values) for key,values in dependencies.items()):
        raise ValueError('dependency map contains unknown context IDs')
    closure_cache = prepared.closures if prepared else {}
    def closure(ids):
        roots = tuple(sorted(ids))
        if roots in closure_cache:
            return closure_cache[roots]
        found=set(ids); pending=list(ids)
        while pending:
            for required in dependencies.get(pending.pop(),[]):
                if required not in found: found.add(required); pending.append(required)
        closure_cache[roots] = frozenset(found)
        return closure_cache[roots]
    start = time.perf_counter_ns()
    query = query_terms(task)
    positions = {item.id: index for index, item in enumerate(items)}
    def in_source_order(selection: list[Item]) -> list[Item]:
        return sorted(selection, key=lambda item: positions[item.id])

    def size(selection: list[Item]) -> int:
        # Tokenizers may merge across boundaries; order can change their count.
        return counter.count(render(in_source_order(selection)))

    # Protected items include user constraints, patches, errors or any caller-pinned data.
    pinned = closure([x.id for x in items if x.protected])
    chosen = [x for x in items if x.id in pinned]
    chosen_size = size(chosen)
    if chosen_size > budget:
        raise ValueError("protected context exceeds budget; increase budget or explicitly revise pins")
    seen = {(x.kind, x.text) for x in chosen}
    decisions = {x.id: "protected" if x.protected else "protected_dependency" for x in chosen}
    candidates, analysis_ms = analyze_importance(task, items, prepared)
    # Individual costs are a screening heuristic only. Every accepted group is
    # still measured in source order, including tokenizer boundary effects.
    # This avoids re-tokenizing a growing context for each oversized candidate.
    eligible = set(pinned)
    for negative_score, _, item in candidates:
        if negative_score < 0 or item.kind not in {'code', 'tool', 'memory'}:
            eligible.update(closure([item.id]))
    cost_items = [item for item in items if item.id in eligible]
    if prepared and prepared._counter is not counter:
        prepared.clear_costs()
        prepared._counter = counter
    cached_costs = prepared.costs if prepared else {}
    missing = [item for item in cost_items if item.id not in cached_costs]
    fragments = [render([item]) for item in missing]
    batch_count = getattr(counter, 'count_many', None)
    costs = batch_count(fragments) if batch_count else [counter.count(x) for x in fragments]
    cached_costs.update({item.id: cost for item, cost in zip(missing, costs)})
    item_cost = {item.id: cached_costs[item.id] for item in cost_items}
    chosen_ids = set(pinned)
    exact_checks = 1
    for negative_score, _, item in sorted(candidates, key=lambda x: (x[0], x[1])):
        if item.id in chosen_ids: continue
        # Code/requirement items can have equal text but different source identities.
        if item.kind in {"tool", "memory"} and (item.kind, item.text) in seen:
            decisions[item.id] = "exact_duplicate"
            continue
        if negative_score >= 0 and item.kind in {'code', 'tool', 'memory'}:
            decisions[item.id] = "irrelevant_drop"
            continue
        candidate = item
        # Extractive tool compression only. Never synthesize facts or truncate protected items.
        if item.kind == "tool" and chosen_size + item_cost[item.id] > budget:
            lines = item.text.splitlines()
            important = [line for line in lines if
                         re.search(r"error|failed|traceback|warning|exit|diff|assert", line, re.I)
                         or terms(line) & query]
            if important and len(important) < len(lines):
                candidate = Item(item.id, item.kind, "\n".join(important), False, item.utility)
        required=[lookup[x] for x in closure([item.id]) if x not in chosen_ids and x!=item.id]
        candidate_cost = item_cost[item.id] if candidate is item else counter.count(render([candidate]))
        estimate = chosen_size + candidate_cost + sum(item_cost[x.id] for x in required)
        # A small slack admits common cross-boundary merges. This may reject a
        # group that fits with an exotic counter; it cannot admit an over-budget
        # group, because exact verification remains authoritative.
        if estimate > budget + 8 * (len(required) + 1):
            decisions[item.id] = "budget_drop"
            continue
        candidate_size = size(chosen + required + [candidate])
        exact_checks += 1
        if candidate_size <= budget:
            chosen.extend(required + [candidate])
            chosen_ids.update(x.id for x in required)
            chosen_ids.add(item.id)
            chosen_size = candidate_size
            for dependency in required: decisions[dependency.id]='dependency_retained'
            seen.add((item.kind, item.text))
            decisions[item.id] = "extractive" if candidate.text != item.text else "retained"
        else:
            decisions[item.id] = "budget_drop"
    chosen = in_source_order(chosen)
    before = counter.count(render(items)) if measure_input else None
    after = chosen_size
    return {"context": render(chosen), "selected": [asdict(x) for x in chosen], 'dependency_map':dependencies,
            "decisions": decisions, "metrics": {
                "counter": counter.name, "input_units": before, "output_units": after,
                "estimated_reduction": None if before is None else 0.0 if before == 0 else 1 - after / before,
                "input_counting": "full diagnostic tokenization" if measure_input else "omitted from request; report model prompt tokens separately",
                "importance_analysis_ms": analysis_ms,
                "governance_ms": (time.perf_counter_ns() - start) / 1e6,
                "exact_candidate_checks": exact_checks,
                "cost_screening": "batched fragments with exact acceptance",
                "prepared_context": prepared is not None,
                "fragment_cost_cache_misses": len(missing),
                "ttft_ms": None, "generation_quality": "not_evaluated"}}
