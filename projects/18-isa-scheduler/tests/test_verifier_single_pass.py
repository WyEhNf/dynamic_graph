import copy
import unittest
from experiments.baseline_r28.isa_scheduler.verify import verify as reference_verify,inspect as reference_inspect
from isa_scheduler.fuzz import generate
from isa_scheduler.model import InvalidBlock
from isa_scheduler.verify import VerificationContext,inspect,verify


def accepted(function,original,output):
    try:function(original,output);return True
    except ValueError:return False


class SinglePassTests(unittest.TestCase):
    def test_symbolic_state_exactly_matches_frozen_verifier(self):
        for seed in range(500):
            data=generate(seed,("wide","branch","highfanout","hazard")[seed%4],2+seed%4)
            self.assertEqual(inspect(data["instructions"]),reference_inspect(data["instructions"]))

    def test_malformed_output_rejection_matches_frozen_grammar(self):
        original=generate(1,"hazard",5)
        base={"block_id":original["block_id"],"optimized_instructions":copy.deepcopy(original["instructions"])}
        modifications=[("id",True),("id",[]),("id",None),("id",0),("op","SLL"),("inputs",None),
                       ("inputs",["t#0"]),("inputs",["t#999"]),("inputs",["t#1","t#2"]),
                       ("reg","") ,("source","t#1"),("unknown",123)]
        for index in range(len(base["optimized_instructions"])):
            for field,value in modifications:
                changed=copy.deepcopy(base);changed["optimized_instructions"][index][field]=value
                self.assertEqual(accepted(verify,original,changed),accepted(reference_verify,original,changed),(index,field,value))
            changed=copy.deepcopy(base);changed["optimized_instructions"][index].pop("id")
            self.assertEqual(accepted(verify,original,changed),accepted(reference_verify,original,changed))

    def test_original_header_and_ids_remain_strict(self):
        data=generate(1,"hazard",5)
        for field,value in (("bit_width",True),("bit_width",6),("block_id",[]),("instructions",{}),("unknown",0)):
            bad=copy.deepcopy(data);bad[field]=value
            with self.assertRaises(InvalidBlock):VerificationContext(bad)
        data["instructions"][2]["id"]=True
        with self.assertRaises(InvalidBlock):VerificationContext(data)

    def test_nonscalar_opcode_is_reported_as_invalid_format(self):
        from isa_scheduler.model import parse_block
        for opcode in ([],{},None,True,3):
            data=generate(1,"hazard",5);data["instructions"][2]["op"]=opcode
            with self.assertRaises(InvalidBlock):VerificationContext(data)
            with self.assertRaises(InvalidBlock):parse_block(data)
