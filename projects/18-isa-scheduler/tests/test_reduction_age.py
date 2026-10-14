import unittest

from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.model import BudgetExceeded, InfeasibleSchedule, parse_block
from isa_scheduler.reduction_age import schedule_reduction_age
from isa_scheduler.verify import IntegerSemantics, interpret, verify
from isa_scheduler.workloads import generate_workload
from scripts.generate_reduction_holdout import generate
from experiments.baseline_phase_r102.optimizer import optimize as old_optimize
from isa_scheduler.optimizer import optimize


class ReductionAgeTests(unittest.TestCase):
    def test_column_role_states_replay_all_original_identities(self):
        for pending in (1, 2):
            for bits in (3, 4, 5):
                data = generate_workload(8010001 + bits, 'dot_product_many', 64, bits)
                output = schedule_reduction_age(parse_block(data), time_budget_ms=5000,
                                                max_pending=pending, max_states=20000)
                verify(data, output)
                check_identity_witness(data, output, output['stats']['original_order'])
                inputs = {row['reg']: i * 23 - 41 for i, row in enumerate(data['instructions']) if row['op'] == 'GET'}
                for semantics in (IntegerSemantics(8, True), IntegerSemantics(16, False), IntegerSemantics(32, True)):
                    self.assertEqual(interpret(data['instructions'], inputs, semantics),
                                     interpret(output['optimized_instructions'], inputs, semantics))
                if bits >= 4:
                    self.assertEqual(output['stats']['inserted_copy_count'], 0)

    def test_restricted_failure_and_budget_are_not_global_unsat(self):
        data = generate_workload(8010011, 'dot_product_many', 64, 2)
        with self.assertRaises(InfeasibleSchedule):
            schedule_reduction_age(parse_block(data))
        data = generate_workload(8010012, 'dot_product_many', 64, 3)
        with self.assertRaises(BudgetExceeded):
            schedule_reduction_age(parse_block(data), max_states=1)
        with self.assertRaises(InfeasibleSchedule):
            schedule_reduction_age(parse_block(generate_workload(8010013, 'hazard_multi', 64, 3)))

    def test_mixed_ordered_operands_and_row_role_permutations(self):
        for rows, bits in ((2, 2), (3, 3), (4, 3)):
            data = generate(8050091 + rows, rows, 11, bits)
            output = schedule_reduction_age(parse_block(data), beam_width=1, time_budget_ms=3000)
            verify(data, output)
            check_identity_witness(data, output, output['stats']['original_order'])
            inputs = {row['reg']: i * 11 - 83 for i, row in enumerate(data['instructions']) if row['op'] == 'GET'}
            for semantics in (IntegerSemantics(8, True), IntegerSemantics(16, False), IntegerSemantics(32, True)):
                self.assertEqual(interpret(data['instructions'], inputs, semantics),
                                 interpret(output['optimized_instructions'], inputs, semantics))

    def test_portfolio_retains_old_zero_and_nonmatching_candidates(self):
        for data in (generate(8050026, 3, 2, 3), generate(8050025, 3, 2, 2)):
            old = old_optimize(data, 'phase_portfolio', time_budget_ms=1000)
            new = optimize(data, 'age_portfolio', time_budget_ms=1000)
            self.assertLessEqual(new['stats']['inserted_copy_count'], old['stats']['inserted_copy_count'])
            verify(data, new)
            check_identity_witness(data, new, new['stats']['original_order'])


if __name__ == '__main__':
    unittest.main()
