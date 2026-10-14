"""Root read-only audit of the G-volume supplement before the sole full run."""
import ast, hashlib, json, shutil, time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/18-isa-scheduler'
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as s:
        for b in iter(lambda:s.read(1024**2),b''): h.update(b)
    return h.hexdigest()
def main():
    prepared=P/'experiments/r188-general-region-G-volume-prepared'
    old=P/'experiments/r186-general-region-full336-prepared'
    m=read(prepared/'source-provenance.json'); prior=read(old/'source-provenance.json')
    assert sha(old/'source-provenance.json')==m['immutable_R186_manifest_sha256']
    assert sha(prepared/'output-volume-plan.json')==m['output_volume_plan_sha256']
    assert hashlib.sha256(json.dumps(m['source_sha256'],sort_keys=True).encode()).hexdigest()==m['source_aggregate_sha256']
    for name,want in m['source_sha256'].items():
        assert sha(P/name)==sha(prepared/'src'/name)==want, name
        if name.endswith('.py'): ast.parse((P/name).read_text(encoding='utf-8'))
    for field in ('initial_files_sha256','prepared_sha256','parameters','count','legal_initials','before_copies'):
        assert m[field]==prior[field],field
    for name,want in m['prepared_sha256'].items(): assert sha(old/name)==want,name
    for key,want in m['initial_files_sha256'].items(): assert sha(old/'initials'/f'{key}.json.gz')==want,key
    inventory=read(old/'inventory.json'); assert len(inventory)==336
    assert len({r['sha256'] for r in inventory})==336 and len({r['family'] for r in inventory})==21
    legal=[r for r in inventory if r['before_copies'] is not None]
    assert len(legal)==272 and sum(r['before_copies'] for r in legal)==192902
    assert sum(r['before_copies']==0 for r in legal)==108 and sum(r['before_copies']>0 for r in legal)==164
    vol=read(prepared/'output-volume-plan.json'); large=Path(vol['large_absolute_directory']); small=Path(vol['small_report_directory'])
    assert large==Path(r'G:\Hackathon-stage2-artifacts\project18\r187-general-region-full336')
    assert small==P/'experiments/r187-general-region-full336'
    assert not large.exists() and not small.exists() and large.parent.resolve()==Path(vol['owned_parent']).resolve()
    assert large.parent.is_dir() and not large.parent.is_symlink()
    assert vol['reserve_bytes']==512*1024**2 and vol['small_F_report_minimum_free_bytes']==64*1024**2
    assert shutil.disk_usage(large.parent).free>vol['uncompressed_global_bound_bytes']+vol['reserve_bytes']
    assert shutil.disk_usage(P).free>64*1024**2
    result=dict(passed=True,reviewed_unix=time.time(),manifest_sha256=sha(prepared/'source-provenance.json'),
        source_aggregate_sha256=m['source_aggregate_sha256'],source_files=len(m['source_sha256']),
        original_inputs=336,families=21,legal_initials=272,initial_COPY=192902,search_routes=164,zero_COPY_retained=108,
        no_incumbent_statuses=dict(Counter(r['source_status'] for r in inventory if r['before_copies'] is None)),
        large_absolute_directory=str(large),small_report_directory=str(small),actual_G_free_bytes=shutil.disk_usage(large.parent).free,
        static_scope='Launcher and incremental raw-ring replay reviewed: original source/dependency/COPY identity and all labels/OPEN/unfinished retained; actual full proposal and best verified. Only output volume changed; no claim of solver execution or official Level.',
        authorization='Exactly one frozen full336 G-volume --run. Retain all 336 including 64 original no-incumbent statuses, all proposals/frontier labels/best and partial failure. Actual G/RAM/F-small gates; no restart, sampling, default promotion or old-evidence deletion.')
    (ROOT/'outputs/stage2-root-general-region-G-volume-r188.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__': main()
