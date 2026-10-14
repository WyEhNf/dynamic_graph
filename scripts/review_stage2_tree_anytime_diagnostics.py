"""Independently replay saved incomplete physical prefixes and immutable labels."""
import hashlib
import json
import subprocess
import time
from collections import Counter
from review_stage2_tree_pair_serial_controls import ROOT,P,replay,fingerprint,distance,sha

def read(p):return json.loads(p.read_text(encoding='utf-8'))

def physical_prefix(item,actions):
    data=item['input'];original=data['instructions'];baseline=item['baseline'];stats=item['stats']
    args=[[i-distance(t) for t in row.get('inputs',[])] for i,row in enumerate(original)]
    users=[set() for row in original]
    for v,operands in enumerate(args):
        for p in operands:users[p].add(v)
    start=stats['rank_interval'][0];rows=[];history=[];done=set();last={};cursor=0
    for row in baseline['output']['optimized_instructions']:
        if cursor==start:break
        if row['op']=='COPY':identity=history[len(rows)-distance(row['source'])]
        else:identity=baseline['original_order'][cursor];done.add(identity);cursor+=1
        rows.append(row);history.append(identity);last[identity]=len(rows)-1
    last={v:p for v,p in last.items() if users[v]-done}
    window=1<<data['bit_width'];sides=stats['sides'];offsets=[0,0]
    for side,offset in actions:
        assert offset==offsets[side];v=sides[side][offset];offsets[side]+=1
        operands=set(args[v]);assert operands<=done
        rotates=0
        while last:
            p=min(last,key=last.get);age=len(rows)-last[p]
            if age<window or p in operands:break
            assert age==window and rotates<window
            rows.append(dict(op='COPY'));last[p]=len(rows)-1;rotates+=1
        assert all(1<=len(rows)-last[p]<=window for p in operands)
        rows.append(dict(op=original[v]['op']));done.add(v)
        for p in operands:
            if not(users[p]-done):del last[p]
        if users[v]-done:last[v]=len(rows)-1
    roles=sorted(last);return offsets,len(rows),roles,[len(rows)-last[v] for v in roles]

def main():
    d=P/'experiments/r170-anytime-diagnostic-boundaries';old=P/'experiments/r168-tree-pair-anytime-gold/src/isa_scheduler/tree_pair_anytime.py'
    source=read(d/'source-provenance.json')
    for name,digest in source['source_sha256'].items():assert sha(d/'src'/name)==digest
    for name,digest in read(d/'evidence-provenance.json')['evidence_sha256'].items():assert sha(P/name)==digest
    a=old.read_text();b=(d/'src/isa_scheduler/tree_pair_anytime.py').read_text();proof=read(d/'unchanged-search-proof.json')
    fragments={'heap_queue':('class _Agenda:','class _Stop','class _Stop'),
        'complete_physical_restore':('        def restore_goal','        initial =','        initial ='),
        'search_goal_prune_interrupt':('        initial =','    # No lower-bound','    # Capture stop')}
    for name,(start,end,endnew) in fragments.items():
        left=a[a.index(start):a.index(end)];right=b[b.index(start):b.index(endnew)]
        assert left==right and hashlib.sha256(left.encode()).hexdigest()==proof['exact_equal_fragments'][name]
    assert sha(old)==proof['before_core_sha256'] and sha(d/'src/isa_scheduler/tree_pair_anytime.py')==proof['after_core_sha256']
    report=read(d/'report.json');outcomes=Counter();full=labels_total=open_total=unfinished_total=0
    for record in report['records']:
        item=read(P/record['returned_result_file']);stats=item['stats'];data=item['input']
        for candidate in (item['baseline'],item['best']):
            cost=replay(data,dict(candidate,input_sha256=fingerprint(data)));full+=1
            if 'copies' in candidate:assert cost==candidate['copies']
        frontier=[json.loads(line) for line in (P/item['frontier_file']).read_text().splitlines()]
        counts=Counter(row['kind'] for row in frontier);assert dict(counts)==item['frontier_record_counts']==record['frontier_record_counts']
        header=frontier[0];assert header['kind']=='frontier_header' and header['actual_open_count']==stats['actual_open_count']==counts['open']
        assert header['unfinished_expansion_present']==(stats['unfinished_expansion'] is not None)==bool(counts['unfinished_expansion'])
        labels={row['label_version']:row for row in frontier if row['kind']=='immutable_path_label'};paths={};physical={}
        for version,label in labels.items():
            predecessor=label['predecessor_label'];assert predecessor is None or predecessor<version
            actions=[] if predecessor is None else list(paths[predecessor])
            if label['action'] is not None:actions.append(label['action'])
            paths[version]=actions
            offsets,g,roles,ages=physical_prefix(item,actions);physical[version]=(roles,ages)
            assert offsets==label['prefixes'] and g==label['g'] and ages==label['ages']
            assert label['h']==len(data['instructions'])-stats['rank_interval'][0]-sum(offsets)
        for row in frontier:
            if row['kind'] not in ('open','unfinished_expansion'):continue
            label=labels[row['label_version']];roles,ages=physical[row['label_version']]
            assert [row['i'],row['j']]==label['prefixes'] and row['g']==label['g'] and row['h']==label['h']
            assert row['roles']==roles and row['ages']==ages
        assert record['search_emit_ms']==stats['elapsed_ms']==stats['search_emit_ms']
        outcomes[stats['outcome']]+=1;labels_total+=len(labels);open_total+=counts['open'];unfinished_total+=counts['unfinished_expansion']
    for path in sorted(d.glob('boundary-*-complete-output.json')):
        row=read(path);replay(row['input'],dict(row['candidate'],input_sha256=fingerprint(row['input'])));full+=1
    assert dict(outcomes)==report['outcomes'] and len(report['records'])==8 and full==21
    folder=ROOT/'outputs/stage2-root-tree-anytime-diagnostics';folder.mkdir(exist_ok=True)
    command="import sys,unittest;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import tests.test_tree_pair_anytime as t;t.ROOT=Path(sys.argv[2]);r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(t));sys.exit(not r.wasSuccessful())"
    proc=subprocess.run(['python','-c',command,str(d/'src'),str(P)],capture_output=True,text=True,timeout=30)
    (folder/'tests.stdout').write_text(proc.stdout);(folder/'tests.stderr').write_text(proc.stderr)
    assert proc.returncode==0 and 'Ran 7 tests' in proc.stderr and '\nOK\n' in proc.stderr
    result=dict(passed=True,reviewed_unix=time.time(),report_sha256=sha(d/'report.json'),source_provenance_sha256=sha(d/'source-provenance.json'),
        returned_results=8,full_output_replays=21,immutable_labels_replayed=labels_total,actual_open_prefixes=open_total,actual_unfinished_prefixes=unfinished_total,
        root_boundary_tests=7,root_exit_code=proc.returncode,outcomes=dict(outcomes),
        scope='Actual saved immutable label paths independently replayed from original operands and incoming physical prefix; g/h/roles/ages and all OPEN/unfinished records agree. Search/heap/physical restore text unchanged. Search time excludes explicit frontier export and JSON I/O. Injected1000ms deadline is contract only; no CLI time guarantee,84/global/official result.')
    (ROOT/'outputs/stage2-root-tree-anytime-diagnostics.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
