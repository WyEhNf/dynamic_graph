"""Preserve actual historical executables and path mappings before rebuilding."""
import json,shutil
from pathlib import Path
from datetime import datetime,timezone
from benchmark_grain48_stage2 import sha


def main():
    project=Path(__file__).resolve().parents[1];root=project/'artifacts/stage2-runtime-release'
    if root.exists():raise SystemExit('Refusing to overwrite release evidence')
    old_default=project/'build/cholesky_runtime.exe';old_memory=project/'build-memory/cholesky_runtime.exe';old_copy=project/'artifacts/stage2-packed-ready/baseline.exe'
    expected={'row':'2b05a6db918ced0c9c9e3bb1bfe5159ea5ed3cfee3ccb0633a538f12de409e62','memory':'7da06bbd96b711f08283c1df2379741f70d8fb2be6727feae586f6c00aaad947'}
    assert sha(old_default)==sha(old_copy)==expected['row'] and sha(old_memory)==expected['memory']
    root.mkdir();historical=root/'historical';historical.mkdir()
    shutil.copyfile(old_default,historical/'row-runtime.exe');shutil.copyfile(old_memory,historical/'memory-runtime.exe')
    provenance=project/'artifacts/final-profiles/build-provenance.json';shutil.copyfile(provenance,historical/'original-build-provenance.json')
    for profile in ('build','build-memory'):
        for name in ('CMakeCache.txt','CMakeFiles/cholesky_core.dir/flags.make','CMakeFiles/cholesky_runtime.dir/link.txt'):
            source=project/profile/name;target=historical/profile/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    mappings=[]
    def find(value,pointer=''):
        if isinstance(value,str):
            normalized=value.replace('\\','/').lower()
            for suffix,label in (('build/cholesky_runtime.exe','row'),('build-memory/cholesky_runtime.exe','memory')):
                if normalized.endswith(suffix):return [{'json_pointer':pointer,'previous_runtime_path':value,'profile':label,'snapshot_path':str(historical/f'{label}-runtime.exe'),'snapshot_sha256':expected[label]}]
        if isinstance(value,dict):return [hit for k,v in value.items() for hit in find(v,pointer+'/'+str(k))]
        if isinstance(value,list):return [hit for i,v in enumerate(value) for hit in find(v,pointer+'/'+str(i))]
        return []
    for path in (project/'artifacts').rglob('*.json'):
        if root in path.parents:continue
        try:old=json.loads(path.read_text(encoding='utf-8'))
        except (ValueError,OSError,UnicodeError):continue
        hits=find(old)
        if hits:mappings.append({'original_artifact':str(path),'artifact_sha256':sha(path),'runtime_path_replacements_for_historical_replay':hits})
    report={'prepared_at_utc':datetime.now(timezone.utc).isoformat(),'status':'historical_snapshots_verified_before_ordinary_build_mutation',
            'snapshot_sha256':{'row':sha(historical/'row-runtime.exe'),'memory':sha(historical/'memory-runtime.exe')},
            'prior_existing_default_snapshot':{'path':str(old_copy),'sha256':sha(old_copy)},'old_provenance_sha256':sha(provenance),
            'path_mappings':mappings,'historical_contract':'Old reports unchanged; when a historical path names ordinary build, use this immutable byte-exact snapshot and original provenance instead. No rewrite of earlier results.'}
    (root/'historical-snapshots.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'snapshots_verified':True,'historical_artifacts_with_build_paths':len(mappings),'root':str(root)}),flush=True)


if __name__=='__main__':main()
