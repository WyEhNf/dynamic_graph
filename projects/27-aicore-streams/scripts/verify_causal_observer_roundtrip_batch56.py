"""Source-only default; --actual future strict saved12 observer equivalence (no solver)."""
from pathlib import Path
import argparse,hashlib,json,re
P=Path('research/batch56');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--actual');args=parser.parse_args()
original=(P/'solution.cpp').read_bytes();instrumented=(P/'observer-solution.cpp').read_bytes().decode('utf-8')
stripped=re.sub(r'/\*R56_OBS_BLOCK_(\d+)_BEGIN\*/.*?/\*R56_OBS_BLOCK_\1_END\*/','',instrumented,flags=re.S)
assert stripped.encode('utf-8')==original and sha(P/'solution.cpp')=='3a4f184de2759fdcd1cbfd899c5f8029e2f7f2691743ec214a895123db19c21a'
inventory=json.loads((P/'observer-return-inventory.json').read_text());assert len(inventory['stage_labels'])<=256
assert len(re.findall(r'/\*R56_OBS_BLOCK_\d+_BEGIN\*/',instrumented))==inventory['marked_blocks']
assert len(re.findall(r'/\*R56_OBS_BLOCK_\d+_END\*/',instrumented))==inventory['marked_blocks']
if not args.actual:
    print(json.dumps(dict(status='SOURCE_ONLY_ROUNDTRIP_ASSERTIONS_PASSED',marked_blocks=inventory['marked_blocks'],source_sha256=sha(P/'solution.cpp'),observer_sha256=sha(P/'observer-solution.cpp'),actual_candidate_execution=False),indent=2));raise SystemExit(0)
freeze=json.loads((P/'observer-source-plan-freeze.json').read_text());plan=json.loads((P/'observer-resource-plan.json').read_text())
for f in freeze['files']:assert sha(f['path'])==f['sha256'],f['path']
actual_path=Path(args.actual);raw=json.loads(actual_path.read_text());before_path=Path(plan['expected_saved_raw_path']);before=json.loads(before_path.read_text())
assert raw['count']==12 and len(raw['cases'])==12 and before['count']==12
baseline={c['name']:c for c in before['cases']};assert len({c['name'] for c in raw['cases']})==12 and {c['name'] for c in raw['cases']}==set(baseline)
rows=[]
for c in raw['cases']:
    core={k:v for k,v in c.items() if k not in ('helper_observer','whole_observer')}
    assert core==baseline[c['name']],(c['name'],'ANY NONOBSERVER FIELD CHANGED')
    for scope in ('helper','whole'):
        o=c[scope+'_observer'];assert not o['counter_overflow'] and not o['state_shape_error']
        assert len(o['metadata'])<=16 and len(o['states'])<=2
        assert o['metadata_seen']-len(o['metadata'])==o['metadata_dropped']
        assert o['states_seen']-len(o['states'])==o['states_dropped']
        assert [x['label'] for x in o['stage_counts']]==inventory['stage_labels']
        for s in o['states']:
            assert s['n']<=4096
            for name in ('original_ids','done','users','degree'):assert len(s[name])==s['n']
            for name in ('prefix_ids','held_ids','pending_ids'):assert len(s[name])<=4096
            assert set(s['prefix_ids'])<=set(s['original_ids']) and len(set(s['prefix_ids']))==len(s['prefix_ids'])
        rows.append(dict(name=c['name'],scope=scope,all_ordinary_fields_identical=True,metadata_seen=o['metadata_seen'],metadata_dropped=o['metadata_dropped'],states_seen=o['states_seen'],states_dropped=o['states_dropped']))
summary=dict(status='ACTUAL_ORIGINAL12_OBSERVER_NONOBSERVER_FIELDS_BYTE_VALUE_IDENTICAL',rows=rows,saved_R56_raw_path=str(before_path),saved_R56_raw_sha256=sha(before_path),actual_observer_path=str(actual_path),actual_observer_sha256=sha(actual_path),source_sha256=sha(P/'solution.cpp'),observer_source_sha256=sha(P/'observer-solution.cpp'),observer_EXE_sha256=sha(plan['exe_path']),algorithm_fields_equal=True,charged_work_evaluations_exhaustion_and_allplans_equal=True,metadata_sampling_not_full_coverage=True,performance_unmeasured=True,default_changed=False)
target=Path(plan['owned_root'])/'outputs/observer-equivalence.json';assert not target.exists();target.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary,indent=2))
