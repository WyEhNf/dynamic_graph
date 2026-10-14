"""Independent certificate arithmetic and raw ancestry; no project imports."""
import copy
import hashlib
import json
import re
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/18-isa-scheduler'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def check(data, certificate):
    assert certificate['kind'] == 'normalized_get_age_potential'
    assert certificate['input_sha256'] == fingerprint(data)
    window = 2 ** data['bit_width']
    assert certificate['window'] == window
    rows = data['instructions']
    assert len({row['id'] for row in rows}) == len(rows)
    selected = certificate['selected_roots']
    assert isinstance(selected, list) and 0 < len(selected) < window
    assert len(set(selected)) == len(selected)
    assert all(type(r) is int and 0 <= r < len(rows) and rows[r]['op'] == 'GET' for r in selected)
    ancestors, consumers = [], [[] for _ in rows]
    for index, row in enumerate(rows):
        assert row['op'] in ('GET', 'SET', 'ADD', 'MULW')
        mask = 0
        for token in row.get('inputs', []):
            assert isinstance(token, str) and re.fullmatch(r't#[1-9][0-9]*', token)
            parent = index - int(token[2:])
            assert 0 <= parent < index and rows[parent]['op'] != 'SET'
            mask |= ancestors[parent] | (1 << parent)
            if index not in consumers[parent]:
                consumers[parent].append(index)
        ancestors.append(mask)
    must_precede_consumer = {}
    for root in selected:
        assert consumers[root]
        mask = 0
        for consumer in consumers[root]:
            mask |= ancestors[consumer]
        must_precede_consumer[root] = mask
    histogram = [0] * (len(selected) + 1)
    for node, ancestors_mask in enumerate(ancestors):
        # Strict root -> node -> a direct consumer, both tests from raw ancestry.
        live_count = sum(bool(ancestors_mask & (1 << root)) and
                         bool(must_precede_consumer[root] & (1 << node)) for root in selected)
        histogram[live_count] += 1
    gain = sum((Fraction(k * amount, window - k) for k, amount in enumerate(histogram) if k), Fraction())
    size = len(selected)
    penalty = Fraction(size * window * (window + 1), (window - size) * (window - size + 1))
    net = gain - penalty
    lower = max(0, -(-net.numerator // net.denominator))
    observed = dict(lower_bound=lower, mandatory_histogram=histogram,
                    gain_fraction=[gain.numerator, gain.denominator],
                    retirement_penalty_fraction=[penalty.numerator, penalty.denominator],
                    net_fraction=[net.numerator, net.denominator])
    for field, value in observed.items():
        assert certificate[field] == value, field
    return lower


def main():
    suites, evidence, tamper_count = {}, {}, 0
    for name, expected_count in [('r129-root-potential-oracle', 400), ('r130-root-potential-positive', 120),
                                 ('r131-root-potential-cross', 16), ('r134-root-potential-336', 336)]:
        directory = PROJECT / 'experiments' / name
        report = json.loads((directory / 'report.json').read_text(encoding='utf-8'))
        wrappers = [json.loads(line) for line in (directory / 'inputs.jsonl').read_text(encoding='utf-8').splitlines()]
        inputs = {fingerprint(wrapper['input']): wrapper['input'] for wrapper in wrappers}
        assert len(inputs) == len(report['records']) == expected_count
        certificates, positive, optimal_positive = 0, 0, 0
        first = None
        for record in report['records']:
            data = inputs[record['sha256']]
            certificate = record['certificate']
            lower = check(data, certificate) if certificate is not None else 0
            assert lower == record['lower']
            certificates += certificate is not None
            positive += lower > 0
            if record['status'] == 'feasible_optimal_copy':
                # Comparison to stored oracle results, not an independent oracle rerun.
                assert lower <= record['copies']
                optimal_positive += lower > 0
            if certificate is not None and first is None:
                first = (data, certificate)
        if first:
            data, certificate = first
            for field, value in [('lower_bound', certificate['lower_bound'] + 1),
                                 ('window', certificate['window'] + 1),
                                 ('input_sha256', '0' * 64),
                                 ('selected_roots', certificate['selected_roots'] * 2),
                                 ('mandatory_histogram', [])]:
                changed = copy.deepcopy(certificate)
                changed[field] = value
                try:
                    check(data, changed)
                except (AssertionError, IndexError, ValueError):
                    tamper_count += 1
                else:
                    raise AssertionError('Accepted tampered ' + field)
        suites[name] = dict(inputs=expected_count, checked_certificates=certificates, positive=positive,
                            stored_oracle_statuses=dict(Counter(r['status'] for r in report['records'])),
                            positive_with_stored_completed_optimal=optimal_positive)
        for filename in ('report.json', 'inputs.jsonl'):
            evidence[(directory / filename).relative_to(ROOT).as_posix()] = sha(directory / filename)
    freeze = PROJECT / 'experiments/r135-root-potential-sources'
    provenance = json.loads((freeze / 'source-provenance.json').read_text(encoding='utf-8'))
    for name, expected in provenance['source_sha256'].items():
        assert sha(freeze / name) == expected, name
    for name, expected in provenance['evidence_sha256'].items():
        assert sha(PROJECT / name) == expected, name
    result = dict(passed=True, reviewed_unix=time.time(), suites=suites, tamper_rejections=tamper_count,
                  frozen_sources=len(provenance['source_sha256']), frozen_evidence=len(provenance['evidence_sha256']),
                  evidence=evidence,
                  scope='Independent raw-ancestor/strict-lifetime predicate and exact rational certificate recomputation. '
                        'Normalized potential proof reviewed separately: selected live-root COPY decreases potential by at most one; '
                        'original emissions contribute k/(W-k); one retirement loss at most W(W+1)/((W-S)(W-S+1)). '
                        'Necessary strict-identity COPY floors only. Stored oracle costs compared; no independent oracle rerun, '
                        'new feasible schedules, global minimum, default promotion or official Level claim.')
    (ROOT / 'outputs/stage2-root-root-potential.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('evidence', 'scope')}))


if __name__ == '__main__':
    main()
