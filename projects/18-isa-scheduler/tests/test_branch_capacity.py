import json
import random
import unittest
from pathlib import Path
from isa_scheduler.branch_capacity import branch_capacity_oracle
from isa_scheduler.model import parse_block
from isa_scheduler.relaxed_capacity import capacity_oracle


class BranchCapacityTests(unittest.TestCase):
    def test_matches_generic_completed_mask_independent_oracle(self):
        outcomes=set()
        for seed in range(80):
            rng=random.Random(seed);rows=[]
            def emit(op,args=(),reg=None):
                index=len(rows);row={"id":index,"op":op}
                if reg is not None:row["reg"]=reg
                if args:row["inputs"]=[f"t#{index-source}" for source in args]
                rows.append(row);return index
            roots=[emit("GET",reg=f"r{i}") for i in range(rng.randint(3,5))]
            # Include all roots in at least one branch, avoiding dead input rows.
            for branch in range(2):
                sequence=roots[:];rng.shuffle(sequence)
                current=emit("ADD",tuple(sequence[:2]))
                for root in sequence[2:]:current=emit("ADD",(current,root))
                emit("SET",(current,),f"out{branch}")
            data={"block_id":f"branch-small-{seed}","bit_width":2,"instructions":rows}
            reference=capacity_oracle(parse_block(data),max_nodes=20,max_states=200000,time_budget_ms=3000)
            compact=branch_capacity_oracle(data,time_budget_ms=3000)
            self.assertNotIn("budget",compact["status"])
            self.assertEqual(reference["outcome"]=="feasible_relaxed_capacity_only",compact["status"]=="relaxed_feasible")
            outcomes.add(compact["status"])
        self.assertEqual(outcomes,{"relaxed_feasible","relaxed_proven_infeasible"})

    def test_last_cross_group_case_is_complete_model_proof(self):
        source=Path(__file__).resolve().parents[1]/"experiments/r18-failure-audit/inputs.jsonl"
        data=next(case["input"] for case in map(json.loads,source.read_text().splitlines()) if case["input"]["block_id"]=="research-cross_group_shared-256-100181")
        proof=branch_capacity_oracle(data,time_budget_ms=3000,max_states=100000)
        self.assertEqual(proof["status"],"relaxed_proven_infeasible")
        self.assertEqual(proof["explored_states"],5321)
        limited=branch_capacity_oracle(data,time_budget_ms=3000,max_states=3)
        self.assertEqual(limited["status"],"state_budget_exhausted")

    def test_invalid_budget_rejected(self):
        with self.assertRaises(ValueError):branch_capacity_oracle({},time_budget_ms=0)
