import unittest
from isa_scheduler.fuzz import generate
from isa_scheduler.incremental import schedule_incremental
from isa_scheduler.model import InfeasibleSchedule, parse_block
from isa_scheduler.verify import IntegerSemantics, interpret, verify


class DeadlineTests(unittest.TestCase):
    def test_500_seeded_cases_two_priorities_independently_checked(self):
        successes = {"deadline":0,"age_first":0}
        for seed in range(920001,920501):
            data=generate(seed,("wide","branch","highfanout","hazard")[seed%4],2+(seed%4))
            block=parse_block(data)
            for policy in successes:
                try:result=schedule_incremental(block,policy)
                except InfeasibleSchedule:continue
                verify(data,result)
                registers={row["reg"]:3*i-7 for i,row in enumerate(data["instructions"]) if row["op"]=="GET"}
                for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False)):
                    self.assertEqual(interpret(data["instructions"],registers,semantics),
                                     interpret(result["optimized_instructions"],registers,semantics))
                successes[policy]+=1
        self.assertGreater(min(successes.values()),450)
