"""Offline strict-identity COPY lower bound from normalized GET ages.

No optimizer state is used. Selected roots must be original GET identities,
fewer than W; births/retirements can be interleaved arbitrarily. COPY-only,
each original once, no identity alias/reread/recompute are essential premises.
"""
from fractions import Fraction
import hashlib
import itertools
import json
from time import perf_counter

from .model import InvalidBlock
from .verify import _original_header, inspect, _reference_distance


def _raw(data):
    _original_header(data); rows = data['instructions']; inspect(rows)
    if any(row['op'] not in ('GET', 'SET', 'ADD', 'MULW') for row in rows):
        raise InvalidBlock('Root potential bound requires original GET/SET/ADD/MULW, no COPY')
    users = [[] for _ in rows]; ancestors = []
    for index, row in enumerate(rows):
        mask = 0
        for source in {index - _reference_distance(token) for token in row.get('inputs', [])}:
            users[source].append(index); mask |= ancestors[source] | 1 << source
        ancestors.append(mask)
    descendants = [0] * len(rows)
    for index in range(len(rows) - 1, -1, -1):
        for consumer in users[index]:
            descendants[index] |= descendants[consumer] | 1 << consumer
    cores = {}
    for root, row in enumerate(rows):
        if row['op'] != 'GET' or not users[root]: continue
        before_future_consumer = 0
        for consumer in users[root]: before_future_consumer |= ancestors[consumer]
        cores[root] = descendants[root] & before_future_consumer
    return rows, users, cores


def _hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _measure(rows, cores, selected, window):
    count = len(selected)
    if not count or count >= window or len(set(selected)) != count:
        raise InvalidBlock('Selected unique original GET count must be in 1..W-1')
    if any(type(root) is not int or root not in cores for root in selected):
        raise InvalidBlock('Selected role must be an original GET index')
    mandatory = [0] * len(rows)
    for root in selected:
        mask = cores[root]
        while mask:
            bit = mask & -mask; mandatory[bit.bit_length() - 1] += 1; mask -= bit
    histogram = [mandatory.count(value) for value in range(count + 1)]
    gain = sum((Fraction(histogram[k] * k, window - k) for k in range(1, count + 1)), Fraction())
    penalty = Fraction(count * window * (window + 1), (window - count) * (window - count + 1))
    net = gain - penalty
    bound = max(0, -(-net.numerator // net.denominator))
    return {'lower_bound': bound, 'mandatory_histogram': histogram,
            'gain_fraction': [gain.numerator, gain.denominator],
            'retirement_penalty_fraction': [penalty.numerator, penalty.denominator],
            'net_fraction': [net.numerator, net.denominator]}


def propose_root_potential_bound(data, *, time_budget_ms=1000, exhaustive_roots=10):
    if time_budget_ms <= 0 or exhaustive_roots < 1: raise ValueError('Positive root-bound budgets required')
    started = perf_counter(); deadline = started + time_budget_ms / 1000
    rows, users, cores = _raw(data); window = 2 ** data['bit_width']
    roots = sorted((root for root in cores if cores[root]), key=lambda root: (-cores[root].bit_count(), root))
    if not roots: return None
    if len(roots) <= exhaustive_roots:
        sets = (subset for size in range(1, min(len(roots), window - 1) + 1)
                for subset in itertools.combinations(roots, size))
        scope = 'exhaustive selected-root subsets only; not exhaustive schedules'
    else:
        sets = (tuple(roots[:size]) for size in range(1, min(len(roots), window - 1) + 1))
        scope = 'ranked root-prefix subsets only; not exhaustive schedules'
    best = None; scanned = 0; budget = False
    for selected in sets:
        if perf_counter() >= deadline: budget = True; break
        measured = _measure(rows, cores, selected, window); scanned += 1
        if best is None or measured['lower_bound'] > best['lower_bound']:
            best = dict(measured, selected_roots=list(selected))
    if best is None: return None
    best.update(kind='normalized_get_age_potential', input_sha256=_hash(data), window=window,
                subsets_scanned=scanned, proposal_budget_exhausted=budget,
                elapsed_ms=(perf_counter() - started) * 1000, proposal_scope=scope,
                proof_scope='Original-once distinct identities, COPY-only; memory hazards may restrict orders further; no alias/reread/recompute')
    return best


def check_root_potential_bound(data, certificate):
    if certificate.get('kind') != 'normalized_get_age_potential' or certificate.get('input_sha256') != _hash(data):
        raise InvalidBlock('Root-potential certificate input/kind mismatch')
    window = 2 ** data['bit_width']
    if certificate.get('window') != window: raise InvalidBlock('Root-potential window mismatch')
    rows, _, cores = _raw(data)
    selected = certificate.get('selected_roots')
    if not isinstance(selected, list): raise InvalidBlock('Selected roots required')
    observed = _measure(rows, cores, selected, window)
    for field in ('lower_bound', 'mandatory_histogram', 'gain_fraction', 'retirement_penalty_fraction', 'net_fraction'):
        if certificate.get(field) != observed[field]: raise InvalidBlock(f'Root-potential {field} mismatch')
    return dict(observed, verified=True, scope='Necessary COPY lower bound in original-once identity model only')
