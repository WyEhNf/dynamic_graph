import unittest
from experiments.baseline_r45.isa_scheduler.verify import interpret as reference, IntegerSemantics as ReferenceSemantics
from isa_scheduler.verify import interpret, IntegerSemantics, _reference_distance
from isa_scheduler.model import InvalidBlock,distance
from isa_scheduler.fuzz import generate


def result(function,rows,inputs,semantics):
    try:return ('ok',function(rows,inputs,semantics))
    except ValueError as exc:return ('error',str(exc))


class InterpreterTransferTests(unittest.TestCase):
    def test_fixed_and_unbounded_models_match_reference(self):
        configs=((8,True,'wrap',4096),(16,False,'wrap',4096),(32,True,'wrap',4096),
                 (8,True,'error',4096),(None,False,'wrap',256))
        for seed in range(500):
            data=generate(seed,('wide','branch','highfanout','hazard')[seed%4],2+seed%4)
            rows=data['instructions']
            inputs={row['reg']:seed%9-3 for row in rows if row['op']=='GET'}
            for config in configs:
                self.assertEqual(result(interpret,rows,inputs,IntegerSemantics(*config)),
                                 result(reference,rows,inputs,ReferenceSemantics(*config)),(seed,config))

    def test_exact_cached_grammar_matches_strict_lexer(self):
        for delta in range(1,1000):self.assertEqual(_reference_distance(f't#{delta}'),distance(f't#{delta}'))
        for token in ('t#0','t#01','t#-1','t#1 ','t#１','T#1','t#1\n',None,True,[],{},1):
            with self.assertRaises(InvalidBlock):_reference_distance(token)

    def test_long_copy_read_write_transfer(self):
        rows=[{'id':0,'op':'GET','reg':'r'}]
        for i in range(1,1000):rows.append({'id':i,'op':'COPY','source':'t#1'})
        rows.extend(({'id':1000,'op':'SET','reg':'r','inputs':['t#1']},{'id':1001,'op':'GET','reg':'r'}))
        for value in (-1000,-128,-1,0,127,1000):
            for mode in ('error','wrap'):
                self.assertEqual(result(interpret,rows,{'r':value},IntegerSemantics(8,True,mode)),
                                 result(reference,rows,{'r':value},ReferenceSemantics(8,True,mode)))
