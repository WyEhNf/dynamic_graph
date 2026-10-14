"""Author local test data and independent functional oracles; not official data."""
import json
from pathlib import Path
from .bundles import digest_tree


CASES = [
 ('clamp', 'Implement clamp(value, lower, upper). Return the value bounded inclusively by lower and upper. Raise ValueError when lower > upper. Values are finite integers.',
  'def clamp(value, lower, upper):\n    if lower > upper:\n        raise ValueError("bounds")\n    return min(upper, max(lower, value))\n',
  '''from solution import clamp
class Check(unittest.TestCase):
    def test_range(self):
        for low in range(-8, 8):
            for high in range(low, 9):
                for value in range(-10, 11):
                    expected = low if value < low else high if value > high else value
                    self.assertEqual(clamp(value, low, high), expected)
    def test_invalid(self):
        with self.assertRaises(ValueError): clamp(1, 3, 2)
''', {}),
 ('chunks', 'Implement chunks(values, size). Return a list of consecutive sublists of at most size elements, preserving order and without modifying values. Raise ValueError for size <= 0. Empty input returns [].',
  'def chunks(values, size):\n    if size <= 0:\n        raise ValueError("size")\n    return [values[i:i+size] for i in range(0, len(values), size)]\n',
  '''from solution import chunks
class Check(unittest.TestCase):
    def test_chunks(self):
        for n in range(35):
            for size in range(1, 12):
                data = list(range(n)); original = data[:]
                result = chunks(data, size)
                self.assertEqual([x for group in result for x in group], original)
                self.assertTrue(all(len(g) == size for g in result[:-1]))
                self.assertTrue(not result or 0 < len(result[-1]) <= size)
                self.assertEqual(data, original)
    def test_invalid(self):
        for size in [0, -1]:
            with self.assertRaises(ValueError): chunks([1], size)
''', {}),
 ('dedupe', 'Implement stable_unique(values) for a list of hashable integers or strings. Return first occurrences in original order. Do not sort or modify input.',
  'def stable_unique(values):\n    return list(dict.fromkeys(values))\n',
  '''from solution import stable_unique
class Check(unittest.TestCase):
    def test_unique(self):
        import random
        rng = random.Random(1103)
        for _ in range(120):
            data = [rng.choice([0, 1, 2, "a", "b", ""]) for _ in range(rng.randrange(30))]
            expected = []
            for x in data:
                if x not in expected: expected.append(x)
            original = data[:]
            self.assertEqual(stable_unique(data), expected)
            self.assertEqual(data, original)
''', {}),
 ('slug', 'Implement slug(text). Lowercase text; replace each run of characters outside ASCII a-z and 0-9 with a single hyphen. Strip leading and trailing hyphens. Empty or all punctuation returns empty string.',
  'import re\ndef slug(text):\n    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")\n',
  '''from solution import slug
class Check(unittest.TestCase):
    def test_examples(self):
        examples = {"Hello, WORLD!": "hello-world", "a___b": "a-b", "": "", "--": "", "42 B": "42-b", "中文 abc": "abc", "a  b   c": "a-b-c"}
        for x, y in examples.items(): self.assertEqual(slug(x), y)
    def test_properties(self):
        import random, string
        rng = random.Random(1104)
        for _ in range(100):
            text = ''.join(rng.choice(string.ascii_letters + string.digits + " ._!") for _ in range(40))
            words = []; current = ''
            for c in text.lower():
                if c in string.ascii_lowercase + string.digits: current += c
                elif current: words.append(current); current = ''
            if current: words.append(current)
            self.assertEqual(slug(text), '-'.join(words))
''', {}),
 ('shipping', 'Implement shipping_fee(weight). Import BASE_FEE, PER_KG, FREE_FROM_KG from config.py. Weight is a nonnegative integer. Return 0 when weight >= FREE_FROM_KG; otherwise BASE_FEE + PER_KG * weight. Negative weight raises ValueError.',
  'from config import BASE_FEE, PER_KG, FREE_FROM_KG\ndef shipping_fee(weight):\n    if weight < 0:\n        raise ValueError("weight")\n    return 0 if weight >= FREE_FROM_KG else BASE_FEE + PER_KG * weight\n',
  '''from solution import shipping_fee
class Check(unittest.TestCase):
    def test_fee(self):
        for weight in range(70):
            self.assertEqual(shipping_fee(weight), 0 if weight >= 23 else 17 + weight * 6)
    def test_invalid(self):
        with self.assertRaises(ValueError): shipping_fee(-1)
    def test_dependency_changes(self):
        import config, importlib, solution
        original = (config.BASE_FEE, config.PER_KG, config.FREE_FROM_KG)
        try:
            for base, rate, threshold in [(3, 2, 5), (9, 7, 3)]:
                config.BASE_FEE, config.PER_KG, config.FREE_FROM_KG = base, rate, threshold
                importlib.reload(solution)
                for weight in range(12):
                    self.assertEqual(solution.shipping_fee(weight), 0 if weight >= threshold else base + weight * rate)
        finally:
            config.BASE_FEE, config.PER_KG, config.FREE_FROM_KG = original
            importlib.reload(solution)
''', {'config.py': 'BASE_FEE = 17\nPER_KG = 6\nFREE_FROM_KG = 23\n'}),
 ('csv_sum', 'Implement total_csv(text). Split a comma-separated string; ignore whitespace-only fields; convert all other fields to int and sum. Invalid integers raise ValueError. Empty text returns 0. Do not silently skip invalid fields.',
  'def total_csv(text):\n    return sum(int(part.strip()) for part in text.split(",") if part.strip())\n',
  '''from solution import total_csv
class Check(unittest.TestCase):
    def test_values(self):
        for text, expected in [("", 0), (", ,", 0), ("1,2,-3", 0), (" 4 , , +7, -9 ", 2), ("8", 8)]:
            self.assertEqual(total_csv(text), expected)
    def test_invalid(self):
        for text in ["1,x", "2,1.2", "nan", "1,--3"]:
            with self.assertRaises(ValueError): total_csv(text)
''', {})
]


def build_suite(destination: Path, cases=None, version=2):
    cases = CASES if cases is None else cases
    for folder in ['spec', 'metadata', 'repo_bundles', 'templates', 'tests', 'oracle']:
        (destination / folder).mkdir(parents=True, exist_ok=True)
    for case_index, (case_id, specification, reference, tests, extra) in enumerate(cases):
        snapshot = destination / 'repo_bundles' / case_id
        snapshot.mkdir(parents=True, exist_ok=True)
        noise_level = {'clamp':1, 'chunks':2, 'dedupe':4, 'slug':8, 'shipping':4, 'csv_sum':8}.get(case_id, 2 + 2 * (case_index % 3))
        expected={'solution.py',*extra,*[f'legacy_{i}.py' for i in range(noise_level)]}
        unexpected={p.relative_to(snapshot).as_posix() for p in snapshot.rglob('*') if p.is_file()}-expected
        if unexpected: raise ValueError(f'fixture directory has unexpected/stale files: {sorted(unexpected)}; use a fresh suite directory')
        (snapshot / 'solution.py').write_text('# Implement the current task here.\n', encoding='utf-8')
        for name, content in extra.items():
            (snapshot / name).parent.mkdir(parents=True, exist_ok=True)
            (snapshot / name).write_text(content, encoding='utf-8')
        # Different bundle sizes test both modest and distractor-heavy engineering contexts.
        for module in range(noise_level):
            unrelated = ''.join(f'def unrelated_{module}_{k}(values):\n    """Legacy telemetry conversion {k}; unrelated to current task."""\n    return [v * {k+2} for v in values]\n\n' for k in range(8))
            (snapshot / f'legacy_{module}.py').write_text(unrelated, encoding='utf-8')
        spec = specification + '\nTarget file: solution.py. Return its complete content. Existing dependencies must stay available.\n'
        (destination / 'spec' / f'{case_id}.md').write_text(spec, encoding='utf-8')
        (destination / 'oracle' / f'{case_id}.py').write_text(reference, encoding='utf-8')
        (destination / 'tests' / f'{case_id}.py').write_text(tests + '\nif __name__ == "__main__": unittest.main()\n', encoding='utf-8')
        noise = '\n'.join(f'INFO telemetry partition {i} finished normally' for i in range(12*noise_level))
        history = [{'kind':'tool', 'text':noise}, {'kind':'tool', 'text':noise},
                   {'kind':'memory', 'text':'Historical request: migrate telemetry dashboards. Already completed.'},
                   {'kind':'tool', 'text':'FAILED current tests: requested function is missing in solution.py', 'protected':True}]
        metadata = {'origin':'self-created; not official Hackathon fixture', 'case_id':case_id,
                    'base_commit':None, 'baseline_bundle':case_id, 'snapshot_sha256':digest_tree(snapshot),
                    'target_file':'solution.py', 'pinned_files':['solution.py'] + list(extra), 'history':history,
                    'seed':1100, 'noise_modules':noise_level, 'dependencies':{'python':'>=3.12', 'external':[]}}
        (destination / 'metadata' / f'{case_id}.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    (destination / 'templates' / 'generation.txt').write_text('Return only the complete target Python file.\n', encoding='utf-8')
    (destination / 'manifest.json').write_text(json.dumps({'origin':'self-created', 'case_ids':[c[0] for c in cases], 'version':version}, indent=2), encoding='utf-8')
    return [c[0] for c in cases]
