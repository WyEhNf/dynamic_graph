"""Root audit of new COPY certificates, using only raw JSON and Python integers.

Does not import the scheduler, its graph representation, or its checkers.
The mathematical proof review is separately recorded with its exact scope.
"""
import hashlib
import json
import re
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P18 = ROOT / 'projects/18-isa-scheduler'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False).encode()).hexdigest()


def raw_graph(data):
    nodes = data['instructions']
    args = []
    regs = {'GET': set(), 'SET': set()}
    ids = set()
    for i, node in enumerate(nodes):
        assert node['id'] not in ids
        ids.add(node['id'])
        op = node['op']
        assert op in ('GET', 'SET', 'ADD', 'MULW')
        sources = []
        for token in node.get('inputs', []):
            assert isinstance(token, str) and re.fullmatch(r't#[1-9][0-9]*', token)
            source = i - int(token[2:])
            assert 0 <= source < i
            sources.append(source)
        assert len(sources) == dict(GET=0, SET=1, ADD=2, MULW=2)[op]
        args.append(tuple(sources))
        if op in regs:
            assert node['reg'] not in regs[op]
            regs[op].add(node['reg'])
    assert not regs['GET'] & regs['SET']
    users = [[] for _ in nodes]
    for i, sources in enumerate(args):
        for source in set(sources):
            users[source].append(i)
    return nodes, args, users


def closure(starts, edges):
    pending = list(starts)
    visited = set()
    while pending:
        node = pending.pop()
        if node not in visited:
            visited.add(node)
            pending.extend(edges[node])
    return visited


corpus_path = P18 / 'experiments/milestone-level-r91-336/inputs.jsonl'
corpus = {fingerprint(row['input']): row['input']
          for line in corpus_path.read_text(encoding='utf-8').splitlines()
          for row in [json.loads(line)]}
bound_path = P18 / 'experiments/r99-reduction-global-audit/report.json'
bound = json.loads(bound_path.read_text(encoding='utf-8'))
assert len(corpus) == len(bound['records']) == 336
assert digest(corpus_path) == bound['corpus_sha256']
checks = []
for record in bound['records']:
    data = corpus[record['sha256']]
    graph = None
    for proof in record['proofs']:
        cert = proof['certificate']
        kind = cert['kind']
        if kind not in ('global_persistent_core_age_sum', 'shared_reduction_accumulator_age_sum'):
            continue
        if graph is None:
            graph = raw_graph(data)
        nodes, args, users = graph
        window = 2 ** data['bit_width']
        assert cert['window'] == window
        witness = cert['witness']
        if kind == 'global_persistent_core_age_sum':
            selected = witness['identities']
            assert 0 < len(selected) < window and len(selected) == len(set(selected))
            common = set(range(len(nodes)))
            for source in selected:
                assert nodes[source]['op'] == 'GET'
                descendants = closure(users[source], users)
                ancestors = closure([s for u in users[source] for s in args[u]], args)
                common &= descendants & ancestors
            k, count = len(selected), len(common)
            slack = window - k
            lower = max(0, (k * count + slack - 1) // slack - k)
            assert witness['forced_core_nodes'] == count
            assert witness['age_sum_range'] == k * slack
            details = dict(selected=k, core_nodes=count)
        else:
            weights, rows = witness['weights'], witness['rows']
            m, r = len(weights), len(rows)
            assert 0 < r < window and m > window
            assert len(set(weights)) == m and all(nodes[i]['op'] == 'GET' for i in weights)
            covered = set(weights)
            for row in rows:
                private, products, adds, terminal = (row[k] for k in
                                                     ('private', 'products', 'additions', 'terminal'))
                assert len(private) == len(products) == len(adds) == m and adds[0] is None
                own = private + products + adds[1:] + [terminal]
                assert len(set(own)) == 3 * m and not covered.intersection(own)
                for j, (x, product) in enumerate(zip(private, products)):
                    assert nodes[x]['op'] == 'GET' and nodes[product]['op'] == 'MULW'
                    assert sorted(args[product]) == sorted((weights[j], x))
                    if j:
                        prior = products[0] if j == 1 else adds[j - 1]
                        assert nodes[adds[j]]['op'] == 'ADD'
                        assert sorted(args[adds[j]]) == sorted((prior, product))
                assert nodes[terminal]['op'] == 'SET' and args[terminal] == (adds[-1],)
                covered.update(own)
            assert covered == set(range(len(nodes)))
            g = max(0, (2 * r + 1) * m - (4 * r + 2) * window)
            slack = window - r
            lower = max(0, (r * g + slack - 1) // slack - r * (m - 1) - r)
            assert witness['forced_nonrefresh_originals'] == g
            details = dict(rows=r, columns=m, forced_nonrefresh_originals=g)
        assert cert['copy_lower_bound'] <= lower
        assert proof['independent']['verified_global_copy_lower_bound'] == lower
        checks.append(dict(sha256=record['sha256'], kind=kind, lower=lower, **details))

successful = [r for r in bound['records'] if r['previous_status'] == 'verified']
assert len(successful) == 272
floor = sum((Fraction(r['copy_lower_bound'], r['original_nodes'] + r['copy_lower_bound'])
             for r in successful), Fraction()) / len(successful)
assert abs(float(floor) - bound['previous_successes_only']['mean_lower_copy_per_output']) < 1e-14
saved_path = P18 / 'experiments/r99-reduction-global-audit/saved-output-audit.json'
saved = json.loads(saved_path.read_text(encoding='utf-8'))
assert saved['compared'] == 272 and not saved['contradictions']
assert saved['bounds_sha256'] == digest(bound_path)

proof_paths = ['research/level-stage/global-core-proof.md',
               'research/level-stage/shared-reduction-proof.md',
               'research/level-stage/forced-cut-proof.md']
result = dict(
    reviewed_unix=time.time(), passed=True,
    method='Root raw-JSON references, DFS closures, complete role coverage and Python integer arithmetic; no project imports.',
    scope='Original identities executed once, ordered original operands, COPY only, pure unique/disjoint GET/SET registers. No rereads, aliases, spill, recomputation or reassociation.',
    checks=checks,
    positive_reduction_certificates=sum(c['kind'] == 'shared_reduction_accumulator_age_sum' for c in checks),
    independent_new_certificates=len(checks),
    successful_subset=dict(count=272, exact_mean_lower_copy_output_numerator=str(floor.numerator),
                           exact_mean_lower_copy_output_denominator=str(floor.denominator),
                           mean_lower_copy_output=float(floor)),
    mathematical_review=[
        'Global core: each counted original is after every selected birth and strictly before a direct consumer of every selected identity. Thus all counted nodes lie within the common persistent interval; core nodes need not form a chain.',
        'At any emission coordinate k distinct latest live identities have age-sum range k(W-k). Each non-refresh original adds k; a COPY can reduce that sum by at most W-k. Take the maximum of overlapping certificates, never their sum.',
        'Shared reductions: before the last row starts at most W columns are born, bounding head GET/MULW by (2R+2)W. After first SET at most W not-fully-consumed weight columns remain, bounding tail GET/MULW by 2RW.',
        'All R logical accumulator roles persist between last product0 and first SET. ADD replaces a role but does not authorize merging or deleting original operations; count all original ADD conservatively.',
        'A legal reference may use an older COPY. Its age is at least the latest copy age; refresh delta R-d_latest >= R-d_used >= -(W-R). The proof requires an inequality, not equality with the used copy.'
    ],
    official_requirement_recheck=dict(
        url='https://www.chaspark.com/#/races/competitions/1326690549003280384',
        observed_date_utc='2026-10-11',
        page_update='2026-10-10 09:18',
        method='Actual page text read through hidden IAB AX state; SPA web fetch alone was insufficient.',
        requirements='Level0 correctness, Level1 average COPY <=10 percent, Level3 <=2 percent plus complexity; no explicit Level2 or averaging/denominator definition in observed body.',
        transformation_scope='Observed body explicitly describes DAG reorder plus COPY; it does not explicitly authorize extra GET/recomputation/spill/aliases/deleting original nodes.'),
    limitation='This lower bound exceeds10 percent on the same272 self-generated successful identities under equal-block COPY/(original+COPY) averaging. It is not an official Level1 failure, an official input-distribution claim, an attainability proof or permission to weaken the identity model.',
    evidence={str(p.relative_to(ROOT)): digest(p) for p in
              [corpus_path, bound_path, saved_path] + [P18 / p for p in proof_paths]})
destination = ROOT / 'outputs/stage2-root-review-r99.json'
destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(passed=True, path=str(destination), new_certificates=len(checks),
                      reduction_certificates=result['positive_reduction_certificates'],
                      subset_lower_mean=float(floor)), ensure_ascii=False))
