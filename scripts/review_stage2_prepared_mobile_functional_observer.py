"""Root review of frozen source preparations; does not invoke any solver."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def save(name,doc):
    (ROOT/'outputs'/name).write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(doc))
def mobile():
    p=ROOT/'projects/18-isa-scheduler';d=p/'experiments/r193-mobile-backbone-prepared';m=read(d/'source-provenance.json')
    assert m['source_aggregate_sha256']=='517ee7d63e279d8a29b1dbe31ccb7b45c2f8aacbfff8b65a19947187b1d5d349'
    assert len(m['source_sha256'])==18
    for rel,s in m['source_sha256'].items():assert sha(p/rel)==sha(d/'src'/rel)==s,rel
    for rel,s in m['prepared_sha256'].items():assert sha(d/rel)==s,rel
    cases=[json.loads(l) for l in (d/'cases.jsonl').read_text(encoding='utf-8').splitlines()]
    old=[json.loads(l) for l in (p/'experiments/r184-general-region-functional-prepared/raw80.jsonl').read_text().splitlines()]
    assert len(cases)==84 and [c['input'] for c in cases[:80]]==old
    statuses={}
    for c in cases:
        data=c['input'];key=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        initial=read(d/'initials'/f'{key}.json')
        assert len(initial['original_order'])==len(data['instructions'])
        if c['kind']=='frozen_tiny80':
            original=p/'experiments/r185-general-region-functional'/f'{key[:16]}-oracle.json';gold=read(original)
            assert sha(original)==sha(d/'gold'/f'{key}.json')==c['old_gold_sha256']
            assert sha(d/'initials'/f'{key}.json')==c['initial_sha256']
            assert c['region']==dict(L=0,R=len(data['instructions'])-1,mobile=list(range(len(data['instructions']))))
            statuses[gold['outcome']]=statuses.get(gold['outcome'],0)+1
    assert statuses=={'optimal':67,'unknown_discovery_budget':13}
    layouts=read(d/'resource-layout.json');assert len(layouts)==84
    assert max(r['package_bytes'] for r in layouts)==m['max_input_package_bytes']<512*1024**2
    assert sum(1024*r['layout']['complete_proposal_bound_bytes'] for r in layouts)==m['global_uncompressed_proposal_upper_bytes']
    assert not Path(m['large_artifact_destination']).exists() and not (p/'experiments/r194-mobile-backbone-small').exists()
    save('stage2-root-mobile-backbone-source-r193.json',dict(passed=True,source_only=True,manifest_sha256=sha(d/'source-provenance.json'),source_files=18,inputs=84,frozen_gold=statuses,max_input_package_bytes=m['max_input_package_bytes'],uncompressed_proposal_bound=m['global_uncompressed_proposal_upper_bytes'],review=['Full state mobile mask/backbone cursor/latest live physical roles; immutable label version parents; g+h safe lower bound; weighted agenda only ordering','Same initial for every region; external suffix live users retained; SET consumes a physical slot; closure>32/fanout reject remain explicit','Independent raw physical-ring Dijkstra includes early and nonlatest COPY, N<=9; unknown is not infeasible; old80 gold is not rerun','Runner verifies every initial/proposal/best and independently replays every emitted frontier; retained resource/budget failures; outputs on G'],authorized_next='One15-contract run then one frozen84 functionality batch; preserve first actual failure. No full336/default/official Level claim.'))
def functional():
    r=Path('G:/Hackathon-stage2-artifacts/project19/load-pair');d=r/'functional-plan-resource-supplement';p=read(d/'plan.json');n=read(r/'next-static-plan/plan.json')
    assert sha(d/'plan.json')=='bfbbf8634dcad7e6afb49ecf455f5783d916d3d6b71bdc7c3a88c292b21eb981'
    for rel,item in p['source_files'].items():assert sha(d/rel)==item['sha256'] and (d/rel).stat().st_size==item['bytes'],rel
    assert p['cases']==n['functional']['cases']+n['functional']['forced_cases']
    assert len(p['cases'])==27 and p['records']==54 and p['unique_C_sources']==19
    cmd=p['compile_command'];flags=(d/'accepted-build/CMakeFiles/cholesky_runtime.dir/flags.make').read_text()
    public=[x for x in cmd if x.startswith('-DCHOL_')]
    assert len(public)==4 and all(x in flags for x in public)
    assert '-fno-fast-math' in cmd and '-ffp-contract=off' in cmd and '-O3' in cmd
    assert p['accepted_core_SHA']=='87414eef783a1ea7122458ab4faa0807fd7598f36be2438501a2febe9b0b8e88'
    assert p['matching_ABI_header_SHA']=='65918905ae87a751b9745bdbf9aae3c5f26644b5aecefbb279731b173fedc3d4'
    assert p['accepted_a95_SHA']=='a95a97d865f7be0942da06b9b35845fd540f88ed05aeaf0bea04d478fbb347e9'
    assert p['compare_permatrix']==['index','n','error','engine','vm_steps','vm_last_pc','lastpc_applicable']
    assert not (r/'functional-evidence').exists()
    save('stage2-root-load-pair-functional-source.json',dict(passed=True,source_only=True,plan_sha256=sha(d/'plan.json'),frozen_files=len(p['source_files']),true_C_sources=19,streams=27,planned_backend_records=54,review=['Observer records finalized real RunMetrics from same execute_owned/ABI/core; never reads C oracle','Fresh all six reference hashes per launch; whole binary stream equality to independent original C','Actual per-matrix steps/PC/errors/engine equality; native PC explicitly inapplicable; fixed1e9 budget and proof features off','One compile with matching PUBLIC macros and strictFP; file stdout/stderr; rejected actual resource observations saved; first failure no retry'],authorized_next='One separate observer compile+functional54; no95 cost pairs until accepted functional results.'))
def negative():
    p=ROOT/'projects/27-aicore-streams';d=p/'research/batch56';m=read(d/'negative-checkpoint.json');a=read(d/'readonly-negative-attribution.json')
    assert sha(d/'negative-checkpoint.json')=='ac02b349b312db47d83693aa8eb1da3d6359e43ffbd1750d41d4a2bdafaffead'
    for item in m['files']:
        file=Path(item['path']);file=file if file.is_absolute() else p/file
        assert sha(file)==item['sha256'] and file.stat().st_size==item['bytes'],str(file)
    before={c['name']:c for c in read(p/'reports/observer-baseline-batch52.json')['cases']}
    now={c['name']:c for c in read('G:/Hackathon-project27-owned/batch56-selected12-79cecf/outputs/selected12.json')['cases']}
    assert len(a['rows'])==12 and {r['name'] for r in a['rows']}==set(now)==set(before)
    for row in a['rows']:
        b=before[row['name']];c=now[row['name']]
        for key in ['work','evaluations','exhausted']:
            assert row['helper_before_'+key]==b['helper'][key] and row['helper_after_'+key]==c['helper'][key]
        assert row['helper_work_delta']==c['helper']['work']-b['helper']['work']
        assert row['helper_valid']==c['helper']['valid'] and row['whole_valid']==c['whole']['valid']
        assert row['whole_before_error']==b['whole']['error'] and row['whole_after_error']==c['whole']['error']
        assert all(row[k] is None for k in ['failure_stage_evidence','selected_pair_evidence','guard_invocation_evidence'])
    source=(d/'solution.cpp').read_text();start=source.index('ShallowResult projection_memory_search(');end=source.index('\n}',start)+2;wrapper=source[start:end]
    assert 'original.work+=cut.work' in wrapper and 'original.exhausted' not in wrapper
    save('stage2-root-causal-negative-design-r56.json',dict(passed=True,static_readonly=True,frozen_files=len(m['files']),actual_original_cases=12,checkpoint_sha256=sha(d/'negative-checkpoint.json'),readonly_attribution_sha256=sha(d/'readonly-negative-attribution.json'),actual_internal_stages_unknown=True,top_exhausted_does_not_merge_cut=True,authorized_next='Source-only bounded independent observer + every-return inventory + marker removal byte-for-byte3a4f + compile/input resource plan; no compiler/solver before review. Defaults and fees unchanged.'))
if __name__=='__main__':mobile();functional();negative()
