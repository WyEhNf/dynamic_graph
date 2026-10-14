import unittest

from context_governance.core import ByteEstimate, Item, PreparedContext, govern


class IncrementalContextTests(unittest.TestCase):
    def test_edits_match_rebuilt_indices_and_do_not_mutate_old_snapshot(self):
        counter = ByteEstimate()
        items = [Item('target','code','def target(): return helper()',True),
                 Item('helper','code','def helper(): return 7'),
                 Item('unused','code','def unrelated(): return 0')]
        graph = {'target':['helper']}
        old = PreparedContext(items,graph)
        original = govern('fix target and helper',items,2000,counter,graph,prepared=old)
        old_costs = old.costs.copy()
        revised_items = [items[0],Item('helper','code','def helper(): return 11'),
                         Item('unused','code','def renamed_extra(): return 3'),
                         Item('config','code','THRESHOLD=12')]
        revised_graph = {'target':['helper'],'helper':['config']}
        revised = old.revised(revised_items,revised_graph)
        fresh = PreparedContext(revised_items,revised_graph)
        for task in ['target helper','renamed extra','THRESHOLD','something absent']:
            actual = govern(task,revised_items,2000,counter,revised_graph,prepared=revised)
            expected = govern(task,revised_items,2000,counter,revised_graph,prepared=fresh)
            for field in ['context','selected','decisions','dependency_map']:
                self.assertEqual(actual[field],expected[field])
            self.assertLessEqual(counter.count(actual['context']),2000)
        self.assertEqual(old.costs,old_costs)
        self.assertEqual(old.items,tuple(items))
        again = govern('fix target and helper',items,2000,counter,graph,prepared=old)
        self.assertEqual(original['selected'],again['selected'])

    def test_removed_nodes_unknown_dependencies_counter_and_aliases(self):
        counter=ByteEstimate()
        items=[Item('a','code','alpha relevant'),Item('b','code','beta relevant')]
        old=PreparedContext(items,{'a':['b']})
        govern('alpha relevant',items,1000,counter,{'a':['b']},prepared=old)
        with self.assertRaises(ValueError): old.revised(items[:1],{'a':['b']})
        with self.assertRaises(ValueError): old.revised([items[0],items[0]],{})
        newer=old.revised(items[:1],{})
        self.assertEqual(newer.closures,{})
        self.assertNotIn('b',newer.costs)
        newer.costs['a']=1
        self.assertNotEqual(old.costs['a'],1)
        result=govern('alpha relevant',items[:1],1000,ByteEstimate(),{},prepared=newer)
        self.assertEqual(result['metrics']['fragment_cost_cache_misses'],1)


if __name__=='__main__': unittest.main()
