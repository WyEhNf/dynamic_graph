"""Static selection/instrumentation/freeze only; never builds or runs a solver."""
import hashlib
import json
from pathlib import Path

sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
p=Path('research/batch52')
classification=json.loads(Path('reports/remaining-static-classification-batch52.json').read_text())['cases']
remaining=json.loads((p/'remaining63-input-only.json').read_text())['cases']
byname={case['name']:case for case in remaining}
selected=[];reasons=[]
rules=[('upper128_projection',lambda r:r['release_cut_static']['initial_upper_all_fit'] and r['projection']['applicable']),
       ('upper128_projection_inapplicable',lambda r:r['release_cut_static']['initial_upper_all_fit'] and not r['projection']['applicable']),
       ('lower_over128',lambda r:r['release_cut_static']['initial_lower_over128']>0),
       ('uncertain_cap',lambda r:not r['release_cut_static']['initial_upper_all_fit'] and not r['release_cut_static']['initial_lower_over128']),
       ('targets_over512',lambda r:r['projection']['reason']=='targets>512'),
       ('targets_below2',lambda r:r['projection']['reason']=='targets<2'),
       ('heldout',lambda r:r['audit_partition']=='heldout'),
       ('largest_edge_count',lambda r:True)]
for label,predicate in rules:
    options=[r for r in classification if predicate(r) and r['name'] not in {c['name'] for c in selected}]
    assert options,label
    options.sort(key=(lambda r:(-r['edges'],r['n'],r['input_sha'])) if label=='largest_edge_count' else (lambda r:(r['n'],r['edges'],r['input_sha'])))
    chosen=options[0];selected.append(byname[chosen['name']]);reasons.append(dict(role=label,name=chosen['name'],features=chosen))
hard=json.loads(Path('data/hard-corpus-resumed.json').read_text())['cases']
recoveries=[]
for batch in (45,48,51):recoveries+=json.loads(Path(f'reports/functional-summary-batch{batch}.json').read_text())['comparisons']['hard']['recovered']
for case in hard:
    if case['name'] in recoveries:
        stripped={key:case[key] for key in ('name','hardware','nodes','deadline_us','expected_feasible')}
        selected.append(stripped);reasons.append(dict(role='existing_recovery_control',name=case['name']))
assert len(selected)==len({c['name'] for c in selected})==12
assert all('witness_plan' not in c and 'generation' not in c for c in selected)
(p/'observer-selected12-input-only.json').write_text(json.dumps(dict(format='aicore-local-v1',cases=selected),indent=2)+'\n',encoding='utf-8')
(p/'selection.json').write_text(json.dumps(dict(status='frozen audit selection,not runtime policy',rules='Eight input feature strata with n/edges/canonical inputSHA tie;four earlier accepted recoveries as controls',selected=reasons),indent=2)+'\n',encoding='utf-8')

oldcut=Path('research/batch51/release-cut.cpp.inc').read_text(encoding='utf-8')
probe,outer=oldcut.split('ShallowResult release_cut_order(',1)
changes=[]
def change(text,before,after,count=1):
    assert text.count(before)==count,(before,text.count(before))
    changes.append((before,after,count));return text.replace(before,after)
probe=change(probe,'  ReleaseCut r;r.peak=r.final_live=live;','  ReleaseCut r;r.peak=r.final_live=live;\n  ObserverFrame frame;frame.kind="probe";frame.producer=producer;frame.bind(g,completed,remaining_users,remaining_degree,live);')
probe=change(probe,'  if(!charge(4*static_cast<I>(g.n)))return r;','  frame.phase="copy";\n  if(!charge(4*static_cast<I>(g.n)))return r;')
probe=change(probe,'  std::vector<int> stack,users=remaining_users,degree=remaining_degree;','  std::vector<int> stack,users=remaining_users,degree=remaining_degree;\n  frame.bind(g,done,users,degree,live);frame.included=&included;frame.phase="closure";')
probe=change(probe,'    if(++count>128)return r;','    if(++count>128){frame.reason="cap128";return r;}')
probe=change(probe,'  for(int i:g.topo){','  frame.phase="topo";\n  for(int i:g.topo){')
probe=change(probe,'  while(r.order.size()<r.pending.size()) {','  frame.phase="greedy";\n  while(r.order.size()<r.pending.size()) {')
probe=change(probe,'    if(selected<0)return r;','    if(selected<0){frame.reason="greedy_stopped";return r;}')
probe=change(probe,'    r.peak=std::max(r.peak,live+v.workspace_memory+v.output_memory);','    frame.phase="apply";frame.transition_incomplete=true;\n    r.peak=std::max(r.peak,live+v.workspace_memory+v.output_memory);')
probe=change(probe,'    for(int c:g.out[i]){if(!charge(1))return r;--degree[c];}','    for(int c:g.out[i]){if(!charge(1))return r;--degree[c];}\n    frame.transition_incomplete=false;frame.phase="greedy";')
probe=change(probe,'  if(users[producer])return r;','  frame.phase="completion";\n  if(users[producer]){frame.reason="producer_unreleased";return r;}')
# Every exit emits BEFORE returning, without changing the returned object.
probe=probe.replace('return r;','{observe_probe_exit(h,g,r,frame,work,limit);return r;}')
outer='ShallowResult release_cut_order('+outer
outer=change(outer,'  ShallowResult r;if(g.n>4096)return r;','  ShallowResult r;ObserverFrame frame;frame.kind="outer";if(g.n>4096){frame.reason="graph_cap4096";return r;}')
outer=change(outer,'  I live=0,peak=0;std::vector<int> prefix;','  I live=0,peak=0;std::vector<int> prefix;\n  frame.bind(g,done,users,degree,live);frame.prefix=&prefix;observer.current_prefix=&prefix;')
outer=change(outer,'    if(have){for(int i:selected.order)if(!apply(i))return r;}','    if(have){for(int i:selected.order)if(!apply(i)){frame.reason="apply_rejected";return r;}}')
outer=change(outer,'    else {if(single<0 || !apply(single))return r;}','    else {if(single<0 || !apply(single)){frame.reason="no_progress";return r;}}')
outer=outer.replace('return r;','{observe_outer_exit(h,g,r,frame,limit);return r;}')
instrumented=probe+outer
# Exact round-trip proof for algorithm text; generic exit hooks reverse first.
roundtrip=instrumented.replace('{observe_probe_exit(h,g,r,frame,work,limit);return r;}','return r;').replace('{observe_outer_exit(h,g,r,frame,limit);return r;}','return r;')
for before,after,count in reversed(changes):
    assert roundtrip.count(after)==count,(after,roundtrip.count(after))
    roundtrip=roundtrip.replace(after,before)
assert roundtrip==oldcut
full=Path('research/batch51/solution.cpp').read_text(encoding='utf-8')
assert full.count(oldcut)==1
helper=(p/'observer.cpp.inc').read_text(encoding='utf-8')
assert instrumented.count('bool cut_charge(')==1
finalcut=instrumented.replace('bool cut_charge(',helper+'\nbool cut_charge(',1)
newfull=full.replace(oldcut,finalcut,1)
wrapper='''  auto cut=release_cut_order(h,g,std::min<I>(2000000,work_limit));
  if(cut.order.size()==static_cast<size_t>(g.n))return cut;
  auto original=projection_memory_search_r48(h,g,work_limit-cut.work);
  original.work+=cut.work;original.evaluations+=cut.evaluations;
  return original;'''
wrapped='''  auto cut=release_cut_order(h,g,std::min<I>(2000000,work_limit));
  observer.cut_work=cut.work;observer.cut_exhausted=cut.exhausted;observer.cut_complete=cut.order.size()==static_cast<size_t>(g.n);
  if(cut.order.size()==static_cast<size_t>(g.n)){observer.total_work=cut.work;return cut;}
  auto original=projection_memory_search_r48(h,g,work_limit-cut.work);
  observer.projection_work=original.work;observer.projection_exhausted=original.exhausted;
  original.work+=cut.work;original.evaluations+=cut.evaluations;
  observer.total_work=original.work;return original;'''
assert newfull.count(wrapper)==1
newfull=newfull.replace(wrapper,wrapped,1)
newfull='#include <sstream>\n#include <string>\n'+newfull
reverse=newfull.removeprefix('#include <sstream>\n#include <string>\n').replace(wrapped,wrapper,1).replace(finalcut,roundtrip,1)
assert reverse==full
(p/'observer-solution.cpp').write_text(newfull,encoding='utf-8')
(p/'observer-cut.cpp.inc').write_text(finalcut,encoding='utf-8')
(p/'instrumentation-roundtrip.json').write_text(json.dumps(dict(status='algorithm text exactly reconstructed after removing pure observation statements/helper',original_raw_sha=sha('research/batch51/solution.cpp'),normalized_original_sha=hashlib.sha256(full.encode()).hexdigest(),reconstructed_sha=hashlib.sha256(reverse.encode()).hexdigest(),observer_sha=sha(p/'observer-solution.cpp'),changes=[dict(original=b,observation=a,count=c) for b,a,c in changes]),indent=2)+'\n',encoding='utf-8')
plan=dict(status='frozen <=12 original input diagnostic only;no branch/full/performance',
          selected_cases=12,failed_cases=8,recovery_controls=4,
          default_source_sha=sha('solution/solution.cpp'),default_exe_sha=sha('build/aicore_bench.exe'),
          default_provenance_sha=sha('research/batch51/provenance.json'),old_tex_sha=sha('reports/project27-research.tex'),
          paths={path:sha(path) for path in ['scripts/prepare_observer_batch52.py','scripts/run_observer_batch52.py',
             'scripts/verify_observer_batch52.py','scripts/make_whole_gold_batch52.py',
             'research/batch52/observer.cpp.inc','research/batch52/observer-solution.cpp','research/batch52/observer-cut.cpp.inc',
             'research/batch52/observer-driver.cpp','research/batch52/instrumentation-roundtrip.json',
             'research/batch52/observer-selected12-input-only.json','research/batch52/selection.json',
             'research/batch52/hand-frontier-counterexample.json','include/problem.h','include/local_json.h',
             'include/simulator.h','include/solver_metrics.h','src/benchmark.cpp','src/simulator.cpp','research/batch51/solution.cpp',
             'research/batch51/numeric_checks.cpp','research/batch51/numeric-validation-ubsan.exe']},
          flags='GCC15.2 -O2 -std=c++17 both source-only driver variants;process-only F-temp;shared functional timing only',
          comparisons='All helper semantic fields/order/work/evaluations/exhausted and wholeSchedulePlan/error/metrics except actual timing identical. Extra observer state excluded from equality,observer counters nevercharged.',
          observer='Counts all exits;up to2 snapshots per reason,complete terminalprefix;done/degree/directusers/live/cut-external held/sink. Snapshots retain original IDs and actual cut subset;cap construction truncation labelled.',
          gold='Independent original3-node bigint lifecycle:cap100 optimal100,greedy rejected;cap120 greedy legal120;exactMAX/aboveMAX controls. No wholedefault failure claim.',
          constraints='No changing comparator/cap/seeds/returnorder,defaultfiles/provenance untouched,no full63/250/perf or algorithmbranch')
(p/'observer-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
print('Static selection/source/plan frozen',sha(p/'observer-plan.json'),flush=True)
