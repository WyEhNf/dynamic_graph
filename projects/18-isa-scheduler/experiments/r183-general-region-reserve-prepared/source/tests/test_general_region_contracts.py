"""R182 declared contracts; frozen unexecuted until root review."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from isa_scheduler.general_region_anytime import RegionAgenda, RegionStop, _prepare, _prefix, _step, resource_layout, search_general_region, iter_region_frontier
from isa_scheduler.general_region_refine import refine_general_regions


def linear_inc(data):
    return {'output':{'block_id':data['block_id'],'optimized_instructions':data['instructions']},
            'original_order':list(range(len(data['instructions'])))}


class Contracts(unittest.TestCase):
    def test_reopen_stale_immutable(self):
        agenda=RegionAgenda(); state=(0,((0,1),)); agenda.offer(state,8,3,None,None)
        agenda.pop(); agenda.expanded[state]=8; agenda.offer(state,7,3,None,None)
        self.assertEqual(agenda.reopens,1); self.assertEqual(agenda.labels[0][1],8)
        agenda.offer(state,6,3,None,None); self.assertEqual(agenda.pop()[2],6)
        self.assertIsNone(agenda.pop()); self.assertEqual(agenda.stale,1)

    def test_oldest_nonlast_operand_copied(self):
        data={'block_id':'nonlast','bit_width':2,'instructions':[
            {'id':0,'op':'GET','reg':'a'},{'id':1,'op':'GET','reg':'b'},
            {'id':2,'op':'GET','reg':'c'},{'id':3,'op':'GET','reg':'d'},
            {'id':4,'op':'ADD','inputs':['t#4','t#3']},
            {'id':5,'op':'ADD','inputs':['t#5','t#1']}]}
        inc={'output':{'block_id':'nonlast','optimized_instructions':[
            {'id':0,'op':'GET','reg':'a'},{'id':1,'op':'GET','reg':'b'},
            {'id':2,'op':'GET','reg':'c'},{'id':3,'op':'GET','reg':'d'},
            {'id':4,'op':'COPY','source':'t#4'},{'id':5,'op':'ADD','inputs':['t#1','t#4']},
            {'id':6,'op':'ADD','inputs':['t#2','t#1']}]},'original_order':list(range(6))}
        graph=_prepare(data,inc,lambda:None)
        moved=_step(graph,4,{0,1,2,3},((0,4),(1,3)),lambda:None)
        self.assertEqual(moved[1][0],{'op':'COPY','source':'t#4'})
        self.assertIn(0,dict(moved[0]))

    def test_copy_before_first_region_original_preserved(self):
        data={'block_id':'prefix','bit_width':2,'instructions':[
            {'id':0,'op':'GET','reg':'a'},{'id':1,'op':'SET','reg':'out','inputs':['t#1']}]}
        inc={'output':{'block_id':'prefix','optimized_instructions':[
            {'id':0,'op':'GET','reg':'a'},{'id':1,'op':'COPY','source':'t#1'},
            {'id':2,'op':'SET','reg':'out','inputs':['t#1']}]},'original_order':[0,1]}
        graph=_prepare(data,inc,lambda:None); prefix,_,roles=_prefix(graph,inc,1,lambda:None)
        self.assertEqual(len(prefix),2); self.assertEqual(roles,((0,1),))

    def test_prepared_wrong_input_and_unsupported(self):
        data={'block_id':'a','bit_width':2,'instructions':[{'id':0,'op':'GET','reg':'x'}]}
        inc=linear_inc(data); prepared=_prepare(data,inc,lambda:None); prepared['raw_data']=dict(data,block_id='b'); prepared['incumbent']=inc
        with self.assertRaises(ValueError): search_general_region(data,inc,0,prepared=prepared)
        with self.assertRaises(ValueError): search_general_region(dict(data,instructions=[{'id':0,'op':'UNKNOWN'}]),inc,0)
        large=dict(data,instructions=[{'id':i,'op':'GET','reg':str(i)} for i in range(16385)])
        with self.assertRaisesRegex(ValueError,'size_unsupported'): search_general_region(large,linear_inc(large),0)

    def test_transition_partial_buffer_not_published(self):
        data={'block_id':'partial','bit_width':2,'instructions':[
            {'id':0,'op':'GET','reg':'a'},{'id':1,'op':'GET','reg':'b'},
            {'id':2,'op':'ADD','inputs':['t#2','t#1']}]}
        inc=linear_inc(data)
        # Add redundant legal COPY to permit exploration under safe f pruning.
        inc['output']['optimized_instructions']=[{'id':0,'op':'GET','reg':'a'},
            {'id':1,'op':'COPY','source':'t#1'},{'id':2,'op':'GET','reg':'b'},
            {'id':3,'op':'ADD','inputs':['t#2','t#1']}]
        result=search_general_region(data,inc,0,max_transitions=1)
        records=list(iter_region_frontier(result['diagnostics']))
        unfinished=next(row for row in records if row['kind']=='unfinished_expansion')
        self.assertEqual(unfinished['phase'],'prepare_neighbors')
        self.assertEqual(result['stats']['accepted_labels'],1)
        self.assertEqual(unfinished['buffered_unpublished'],1)

    def test_region_cap_continues_and_budget_retains_best(self):
        data={'block_id':'dispatch','bit_width':2,'instructions':[
            {'id':i,'op':'GET','reg':str(i)} for i in range(48)]}
        inc=linear_inc(data); rows=[]
        for i in range(48):
            rows.append({'id':len(rows),'op':'GET','reg':str(i)})
            if i in (1,17,33): rows.append({'id':len(rows),'op':'COPY','source':'t#1'})
        inc['output']['optimized_instructions']=rows; calls=[]
        def child(*args,**kwargs):
            calls.append(args[2]); outcome='partial_outlet_limit' if len(calls)==1 else 'partial_state_budget'
            return {'best':inc,'diagnostics':None,'stats':{'outcome':outcome,'processed_states':1,'attempted_transitions':1}}
        with patch('isa_scheduler.general_region_refine.search_general_region',side_effect=child):
            result=refine_general_regions(data,inc)
        self.assertEqual(len(calls),2); self.assertEqual(len(result['stats']['outlet_limited_regions']),1)
        self.assertEqual(result['best']['copies'],3)

    def test_resource_records_bounds(self):
        data={'block_id':'layout','bit_width':5,'instructions':[{'id':0,'op':'GET','reg':'long'*1000}]}
        layout=resource_layout(data,linear_inc(data))
        self.assertLessEqual(layout['label_record_bound_bytes'],1024)
        self.assertLessEqual(layout['open_record_bound_bytes'],2048)
        self.assertGreater(layout['complete_proposal_bound_bytes'],4000)

    def test_set_dead_get_suffix_and_hazard(self):
        data={'block_id':'hazard','bit_width':2,'instructions':[
            {'id':0,'op':'GET','reg':'a'},{'id':1,'op':'SET','reg':'a','inputs':['t#1']},
            {'id':2,'op':'GET','reg':'a'},{'id':3,'op':'GET','reg':'unused'},
            {'id':4,'op':'SET','reg':'out','inputs':['t#2']}]}
        graph=_prepare(data,linear_inc(data),lambda:None)
        self.assertIsNone(_step(graph,2,{0},((0,1),),lambda:None))
        live,_=_step(graph,1,{0},((0,1),),lambda:None); self.assertEqual(live,())
        live,_=_step(graph,2,{0,1},live,lambda:None); self.assertEqual(live,((2,1),))
        live,_=_step(graph,3,{0,1,2},live,lambda:None); self.assertEqual(live,((2,2),))
        live,_=_step(graph,4,{0,1,2,3},live,lambda:None); self.assertEqual(live,())

    def test_saved_complete_before_resource_stop_retained(self):
        data={'block_id':'complete','bit_width':2,'instructions':[
            {'id':0,'op':'GET','reg':'a'},{'id':1,'op':'GET','reg':'b'},
            {'id':2,'op':'ADD','inputs':['t#2','t#1']}]}
        inc={'output':{'block_id':'complete','optimized_instructions':[
            {'id':0,'op':'GET','reg':'a'},{'id':1,'op':'COPY','source':'t#1'},
            {'id':2,'op':'GET','reg':'b'},{'id':3,'op':'ADD','inputs':['t#2','t#1']}]},'original_order':[0,1,2]}
        saved=[]
        def sink(candidate):
            saved.append(candidate); raise RegionStop('producer_resource_reserve_after_saved_complete')
        result=search_general_region(data,inc,0,on_completed=sink)
        self.assertEqual(len(saved),1); self.assertEqual(result['best']['copies'],0)
        self.assertEqual(result['stats']['complete_outputs'],1)
        self.assertIn('resource_reserve',result['stats']['outcome'])

    def test_resource_preflight_unknown_baseline_fallback(self):
        data={'block_id':'space','bit_width':2,'instructions':[{'id':0,'op':'GET','reg':'a'}]}
        inc=linear_inc(data)
        with patch('isa_scheduler.general_region_refine.search_general_region') as child:
            result=refine_general_regions(data,inc,resource_snapshot=lambda:{'disk_free_bytes':1})
        child.assert_not_called(); self.assertEqual(result['best']['output'],inc['output'])
        self.assertEqual(result['stats']['outcome'],'partial_resource_preflight_unknown')


if __name__=='__main__': unittest.main()
