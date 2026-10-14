"""Extend frozen 10 DEV public contracts to all 30 using only public specs.

The first 10 frozen files are never changed. This emits a separate all30
manifest. The candidate runner must verify that manifest when using extension
files; old v26 smoke continues using the original 10-case manifest.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ADAPTER=ROOT/'adapters'/'correctness-v26'
SUITE=ROOT/'fixtures'/'combined-public-v17'

CHECKS={
'clamp':'''from solution import clamp
class PublicContract(unittest.TestCase):
    def test_values_and_reversed_bounds(self):
        for low in range(-3,4):
            for high in range(low,4):
                for value in range(-5,6):
                    actual=clamp(value,low,high)
                    self.assertTrue(low<=actual<=high)
                    self.assertEqual(actual,value if low<=value<=high else low if value<low else high)
        with self.assertRaises(ValueError): clamp(0,2,1)
''',
'chunks':'''from solution import chunks
class PublicContract(unittest.TestCase):
    def test_partition_order_size_and_no_mutation(self):
        for values in ([],[1],[3,1,3,2,4]):
            for size in (1,2,3,8):
                frozen=copy.deepcopy(values); actual=chunks(values,size)
                self.assertEqual([x for part in actual for x in part],values)
                self.assertTrue(all(0<len(part)<=size for part in actual))
                self.assertTrue(all(len(part)==size for part in actual[:-1]))
                self.assertEqual(values,frozen)
        for size in (0,-2):
            with self.assertRaises(ValueError): chunks([],size)
''',
'csv_sum':'''from solution import total_csv
class PublicContract(unittest.TestCase):
    def test_whitespace_blanks_integers_and_invalid_fields(self):
        self.assertEqual(total_csv(''),0)
        self.assertEqual(total_csv(' , -2, 5,, +3, '),6)
        for text in ('1,bad,2','1,2.5','1,+'):
            with self.assertRaises(ValueError): total_csv(text)
''',
'dedupe':'''from solution import stable_unique
class PublicContract(unittest.TestCase):
    def test_first_seen_order_and_input(self):
        values=[3,'a',1,3,'a',2,'b',1]; frozen=copy.deepcopy(values)
        actual=stable_unique(values)
        self.assertEqual(actual,[3,'a',1,2,'b'])
        self.assertEqual(values,frozen)
        self.assertEqual(stable_unique([]),[])
        self.assertEqual(stable_unique(actual),actual)
''',
'histogram':'''from solution import histogram
class PublicContract(unittest.TestCase):
    def test_counts_first_seen_and_input(self):
        values=['b',2,'b',1,2,'a']; frozen=copy.deepcopy(values)
        actual=histogram(values)
        self.assertEqual(actual,{'b':2,2:2,1:1,'a':1})
        self.assertEqual(list(actual),['b',2,1,'a'])
        self.assertEqual(values,frozen)
        self.assertEqual(histogram([]),{})
''',
'prefix':'''from solution import common_prefix
class PublicContract(unittest.TestCase):
    def test_unicode_case_empty_and_no_mutation(self):
        for values,expected in [([],''),(['flower','flow','flight'],'fl'),(['中文甲','中文乙'],'中文'),(['A','a'],''),(['abc',''],''),(['alone'],'alone')]:
            frozen=copy.deepcopy(values)
            self.assertEqual(common_prefix(values),expected)
            self.assertEqual(values,frozen)
''',
'rotate':'''from solution import rotate
class PublicContract(unittest.TestCase):
    def test_modular_right_rotation_fresh_and_input(self):
        values=[1,2,3,4]; frozen=values[:]
        for offset in range(-10,11):
            actual=rotate(values,offset)
            self.assertIsNot(actual,values)
            self.assertEqual(actual, [values[(i-offset)%len(values)] for i in range(len(values))])
            self.assertEqual(rotate(actual,-offset),values)
            self.assertEqual(values,frozen)
        self.assertEqual(rotate([],100),[])
''',
'runs':'''from solution import runs
class PublicContract(unittest.TestCase):
    def test_consecutive_runs_and_input(self):
        values=[3,3,1,3,2,2]; frozen=values[:]
        actual=runs(values)
        self.assertEqual(actual,[(3,2),(1,1),(3,1),(2,2)])
        self.assertEqual([v for v,n in actual for _ in range(n)],values)
        self.assertEqual(values,frozen)
        self.assertEqual(runs([]),[])
''',
'slug':'''from solution import slug
class PublicContract(unittest.TestCase):
    def test_ascii_runs_lowercase_and_edges(self):
        for text,expected in [('', ''),('!?!',''),('  HELLO...World 99 ','hello-world-99'),('a中文b','a-b'),('A__--B','a-b'),('123','123')]:
            self.assertEqual(slug(text),expected)
            self.assertEqual(slug(slug(text)),expected)
''',
'window':'''from solution import window_sums
class PublicContract(unittest.TestCase):
    def test_sums_sizes_and_input(self):
        values=[2,-1,4,0,3]; frozen=values[:]
        for size in (1,2,3,5,8):
            self.assertEqual(window_sums(values,size),[sum(values[i:i+size]) for i in range(max(0,len(values)-size+1))])
            self.assertEqual(values,frozen)
        self.assertEqual(window_sums([],1),[])
        for size in (0,-1):
            with self.assertRaises(ValueError): window_sums(values,size)
''',
'shipping':'''import solution
import config
class PublicContract(unittest.TestCase):
    def test_configured_boundary_and_negative(self):
        for weight in (0,max(0,config.FREE_FROM_KG-1),config.FREE_FROM_KG,config.FREE_FROM_KG+2):
            self.assertEqual(solution.shipping_fee(weight),0 if weight>=config.FREE_FROM_KG else config.BASE_FEE+config.PER_KG*weight)
        with self.assertRaises(ValueError): solution.shipping_fee(-1)
''',
'threshold':'''import solution
import config
from unittest.mock import patch
class PublicContract(unittest.TestCase):
    def test_helper_controls_predicate_and_no_mutation(self):
        values=[2,8,2,-1]; frozen=values[:]
        with patch.object(solution,'inclusive',side_effect=lambda value,limit:value==2) as helper:
            self.assertEqual(solution.accepted(values),[2,2])
            self.assertEqual([c.args for c in helper.call_args_list],[(v,config.LIMIT) for v in values])
        self.assertEqual(values,frozen)
        self.assertEqual(solution.accepted([]),[])
''',
'bounded_mean':'''import solution
from unittest.mock import patch
class PublicContract(unittest.TestCase):
    def test_helper_return_controls_mean_and_input(self):
        values=[-9,2,80]; frozen=values[:]
        with patch.object(solution,'bounded',side_effect=lambda value:2*value+1) as helper:
            actual=solution.bounded_mean(values)
            self.assertIsInstance(actual,float)
            self.assertAlmostEqual(actual,sum(2*v+1 for v in values)/len(values))
            self.assertEqual([c.args[0] for c in helper.call_args_list],values)
        self.assertEqual(values,frozen)
        with self.assertRaises(ValueError): solution.bounded_mean([])
''',
'choose_records':'''import solution
from unittest.mock import patch
class PublicContract(unittest.TestCase):
    def test_helper_records_order_duplicates_and_fresh_list(self):
        records=[('a',2),('b',3),('a',2),('c',0)]; frozen=records[:]
        with patch.object(solution,'qualifies',side_effect=lambda priority:priority==2) as helper:
            actual=solution.choose_records(records)
            self.assertEqual(actual,[records[0],records[2]])
            self.assertIsNot(actual,records)
            self.assertIs(actual[0],records[0])
            self.assertEqual([c.args[0] for c in helper.call_args_list],[2,3,2,0])
        self.assertEqual(records,frozen)
        self.assertEqual(solution.choose_records([]),[])
''',
'parse_records':'''import solution
from unittest.mock import patch
class PublicContract(unittest.TestCase):
    def test_helper_every_nonblank_line_order_and_errors(self):
        text='first\\n  \\nsecond\\nfirst'
        def parse(line):
            return (line.strip(),len(line.strip()))
        with patch.object(solution,'parse_record',side_effect=parse) as helper:
            self.assertEqual(solution.parse_records(text),[('first',5),('second',6),('first',5)])
            self.assertEqual([c.args[0].strip() for c in helper.call_args_list],['first','second','first'])
        with patch.object(solution,'parse_record',side_effect=ValueError('public malformed')):
            with self.assertRaises(ValueError): solution.parse_records('malformed')
        self.assertEqual(solution.parse_records('  \\n'),[])
''',
'partition_even':'''import solution
from unittest.mock import patch
class PublicContract(unittest.TestCase):
    def test_helper_partition_order_duplicates_fresh_lists(self):
        values=[1,2,1,4,3]; frozen=values[:]
        with patch.object(solution,'is_even',side_effect=lambda value:value==1) as helper:
            even,other=solution.partition_even(values)
            self.assertEqual((even,other),([1,1],[2,4,3]))
            self.assertIsNot(even,values); self.assertIsNot(other,values); self.assertIsNot(even,other)
            self.assertEqual([c.args[0] for c in helper.call_args_list],values)
        self.assertEqual(values,frozen)
        self.assertEqual(solution.partition_even([]),([],[]))
''',
'priced_total':'''import solution
import config
from unittest.mock import patch
class PublicContract(unittest.TestCase):
    def test_helper_cost_and_configured_discount_and_input(self):
        rows=[(1,2),(3,4)]; frozen=rows[:]
        with patch.object(solution,'checked_cost',side_effect=lambda quantity,price:config.TRIGGER) as helper:
            self.assertEqual(solution.priced_total(rows),2*config.TRIGGER-config.DISCOUNT)
            self.assertEqual([c.args for c in helper.call_args_list],rows)
        self.assertEqual(rows,frozen)
        self.assertEqual(solution.priced_total([]),0)
        with self.assertRaises(ValueError): solution.priced_total([(-1,2)])
''',
'summarize_pairs':'''import solution
from unittest.mock import patch
class PublicContract(unittest.TestCase):
    def test_helper_normalized_order_sums_and_input(self):
        pairs=[(' B ',2),('a',3),('b',4),(' A',-1)]; frozen=pairs[:]
        with patch.object(solution,'normalize_key',side_effect=lambda key:key.strip().lower()) as helper:
            actual=solution.summarize_pairs(pairs)
            self.assertEqual(actual,{'b':6,'a':2})
            self.assertEqual(list(actual),['b','a'])
            self.assertEqual([c.args[0] for c in helper.call_args_list],[key for key,value in pairs])
        self.assertEqual(pairs,frozen)
        self.assertEqual(solution.summarize_pairs([]),{})
''',
'allocate_round_robin':'''import solution
class PublicContract(unittest.TestCase):
    def test_round_order_surplus_empty_validation_and_input(self):
        for demands,total,expected in [([1,4,2],5,[1,2,2]),([3,3,3],4,[2,1,1]),([1,0,2],20,[1,0,2]),([],5,[]),([2,2],0,[0,0])]:
            frozen=demands[:]
            actual=solution.allocate_round_robin(demands,total)
            self.assertEqual(actual,expected)
            self.assertIsNot(actual,demands)
            self.assertEqual(demands,frozen)
        for demands,total in [([], -1),([1,-1],2),([1,1.5],2),([1],2.5)]:
            with self.assertRaises(ValueError): solution.allocate_round_robin(demands,total)
''',
'shortest_layers':'''import solution
from unittest.mock import patch
class PublicContract(unittest.TestCase):
    def test_layers_duplicates_cycles_unreachable_validation_and_input(self):
        edges=[(0,2),(0,1),(2,3),(1,3),(3,0),(0,2)]; frozen=edges[:]
        self.assertEqual(solution.shortest_layers(5,edges,0),[[0],[1,2],[3]])
        self.assertEqual(edges,frozen)
        for n,edges,start in [(5,[(4,5)],0),(2,[],2),(-1,[],0)]:
            with self.assertRaises(ValueError): solution.shortest_layers(n,edges,start)
        with patch.object(solution,'checked_size',wraps=solution.checked_size) as size, patch.object(solution,'checked_vertex',wraps=solution.checked_vertex) as vertex:
            self.assertEqual(solution.shortest_layers(3,[(1,2)],0),[[0]])
            self.assertTrue(size.called)
            for endpoint in (0,1,2): self.assertTrue(any(c.args==(endpoint,3) for c in vertex.call_args_list))
''',
}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    old=json.loads((ADAPTER/'contract-manifest.json').read_text(encoding='utf-8'))
    for case_id,entry in old['cases'].items():
        if sha(ADAPTER/'public_contracts'/f'{case_id}.py')!=entry['test_sha256']: raise ValueError('original frozen public contract changed')
    for case_id,body in CHECKS.items():
        source='import copy\nimport unittest\n'+body
        compile(source,f'{case_id}.py','exec')
        path=ADAPTER/'public_contracts'/f'{case_id}.py'
        if path.exists() and path.read_text(encoding='utf-8')!=source: raise ValueError('refuse changing existing public checks')
        if not path.exists(): path.write_text(source,encoding='utf-8')
    ids=json.loads((SUITE/'manifest.json').read_text(encoding='utf-8'))['case_ids']
    if set(ids)!=set(old['cases'])|set(CHECKS): raise ValueError('public contract coverage mismatch')
    manifest={'version':'public-contracts-all30-v26','origin':'Public-spec derived, manually authored, development-informed DEV checks; not holdout, proof or official suite',
              'original10_manifest_sha256':sha(ADAPTER/'contract-manifest.json'),
              'script_sha256':sha(Path(__file__)),'suite_manifest_sha256':sha(SUITE/'manifest.json'),
              'cases':{case_id:{'spec_sha256':sha(SUITE/'spec'/f'{case_id}.md'),'test_sha256':sha(ADAPTER/'public_contracts'/f'{case_id}.py')} for case_id in ids}}
    path=ADAPTER/'all30-contract-manifest.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=manifest: raise ValueError('frozen all30 public contract changed')
    if not path.exists(): path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'public_contracts':len(ids),'manifest_sha256':sha(path)}))

if __name__=='__main__': main()
