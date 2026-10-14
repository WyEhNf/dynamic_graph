import unittest
from context_governance.core import ByteEstimate, Item, PreparedContext, govern


class TestPreparedContext(unittest.TestCase):
    def test_cached_policy_matches_uncached_across_tasks_and_counters(self):
        class Counting(ByteEstimate):
            def __init__(self): self.batch_items=0; self.exact=0
            def count(self,text): self.exact+=1; return super().count(text)
            def count_many(self,texts):
                self.batch_items+=len(texts)
                return [super(Counting,self).count(text) for text in texts]
        items=[Item('r','requirement','Preserve errors',True),
               Item('parser','code','def parser(x): return helper(x)'),
               Item('helper','code','def helper(x): return x'),
               Item('metrics','code','def metrics(x): return x*x')]
        deps={'parser':['helper']}; prepared=PreparedContext(items,deps); counter=Counting()
        for task in ['parser','metrics','parser']:
            cached=govern(task,items,130,counter,deps,False,prepared)
            plain=govern(task,items,130,ByteEstimate(),deps,False)
            for key in ['context','selected','decisions','dependency_map']:
                self.assertEqual(cached[key],plain[key])
            self.assertLessEqual(counter.count(cached['context']),130)
        self.assertEqual(counter.batch_items,4)
        new_counter=Counting()
        govern('parser',items,130,new_counter,deps,False,prepared)
        self.assertEqual(new_counter.batch_items,3)

    def test_stale_inputs_are_rejected_without_using_cached_selection(self):
        items=[Item('r','requirement','original',True),Item('a','code','foo')]
        prepared=PreparedContext(items)
        changed=[Item('r','requirement','changed',True),items[1]]
        with self.assertRaisesRegex(ValueError,'stale'): govern('foo',changed,100,prepared=prepared)
        with self.assertRaisesRegex(ValueError,'stale'): govern('foo',items,100,dependencies={'a':['r']},prepared=prepared)


if __name__=='__main__': unittest.main()
