import copy,random,unittest
from isa_scheduler.model import parse_block
from isa_scheduler.terminal_pairs import recognize,schedule_terminal_pairs
from isa_scheduler.optimizer import optimize
from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.verify import verify
from isa_scheduler.workloads import generate_workload,FAMILIES


class TerminalPairsTests(unittest.TestCase):
    def test_160_fresh_complete_groups_match_exact_copy_formula(self):
        for seed in range(160):
            size=random.Random(seed).randrange(8,257)
            data=generate_workload(5000001+seed,'terminal_root_pairs',size,2)
            block=parse_block(data);candidate=schedule_terminal_pairs(block,time_budget_ms=1000)
            verify(data,candidate);check_identity_witness(data,candidate,candidate['stats']['original_order'])
            self.assertTrue(candidate['stats']['terminal_formula_matched'])
            actual=optimize(data,time_budget_ms=1000)
            self.assertEqual(actual['stats']['inserted_copy_count'],candidate['stats']['inserted_copy_count'])
            if actual['stats']['inserted_copy_count']:
                proof=actual['stats']['optimality_certificate']
                self.assertEqual(proof['tolerance'],0)
                self.assertEqual(proof['copy_lower_bound'],actual['stats']['inserted_copy_count'])
                self.assertEqual(actual['stats']['search']['outcome'],'optimal_under_model')
                self.assertIn('independent_identity_witness',proof)
                self.assertNotIn('approximation_certificate',actual['stats'])

    def test_strict_shape_and_register_scope_screens(self):
        data=generate_workload(500001,'terminal_root_pairs',64,2)
        self.assertIsNotNone(recognize(parse_block(data)))
        for family in FAMILIES:
            if family=='ordered_duplicate_network':continue
            self.assertIsNone(recognize(parse_block(generate_workload(500001,family,128,2))))
        self.assertIsNone(recognize(parse_block({**data,'bit_width':3})))
        self.assertIsNone(recognize(parse_block(data,'conservative')))
        bad=copy.deepcopy(data);bad['instructions'][-1]['reg']=bad['instructions'][0]['reg']
        self.assertIsNone(recognize(parse_block(bad)))
        bad=copy.deepcopy(data);bad['instructions'][-1]['inputs']=bad['instructions'][-2]['inputs'][:]
        # Rebase the token to refer to the same source as the preceding SET.
        bad['instructions'][-1]['inputs']=[f"t#{int(bad['instructions'][-2]['inputs'][0][2:])+1}"]
        self.assertIsNone(recognize(parse_block(bad)))

    def test_unused_get_is_preserved_and_not_born_before_live_group(self):
        data=generate_workload(500001,'terminal_root_pairs',64,2)
        data['instructions'].append({'id':len(data['instructions']),'op':'GET','reg':'unused'})
        result=optimize(data,time_budget_ms=1000);verify(data,result)
        check_identity_witness(data,result,result['stats']['original_order'])
        self.assertEqual(result['optimized_instructions'][-1]['reg'],'unused')
