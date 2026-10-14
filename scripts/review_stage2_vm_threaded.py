"""Independently inspect every saved whole-C output and rerun frozen contracts."""
import json
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from review_stage2_vm_measurements import compare_files, sha

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'projects/19-dynamic-graph/artifacts/stage2-prepared-vm-phase3'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    manifest_path = STAGE/'small-contract-manifest.json'
    manifest = read(manifest_path)
    for name,expected in manifest['source_sha256'].items():
        assert sha(STAGE/'candidate-source'/name)==expected,name
    for name,expected in manifest['executable_sha256'].items():
        assert sha(STAGE/name)==expected,name
    native = []
    for row in manifest['contracts']:
        run = subprocess.run([str(STAGE/row['name'])],capture_output=True,text=True,check=True,timeout=30)
        result = json.loads(run.stdout)
        assert result==row['result'] and not run.stderr
        native.append(dict(name=row['name'],result=result))
    report_path = STAGE/'correctness/report.json'
    report = read(report_path)
    assert report['passed'] and report['status']=='complete'
    assert sha(manifest_path)==report['small_manifest_sha256']
    assert len(report['sources'])==13 and len(report['runs'])==378
    for row in report['sources']:
        base=Path(row['source']).parent
        for name,key in [('source.c','source_sha256'),('program.meta','metadata_sha256'),
                         ('oracle.c','harness_sha256'),('oracle.exe','oracle_binary_sha256')]:
            assert sha(base/name)==row[key],(row['label'],name)
    for row in report['backends'].values():
        assert sha(Path(row['exe']))==row['sha256']
    families=defaultdict(list)
    for row in report['runs']:
        size,hashes=compare_files([Path(row['reference']),Path(row['output'])])
        assert size==row['bytes'] and hashes[0]==hashes[1]==row['sha256']==row['reference_sha256']
        assert sha(Path(row['input']))==row['input_sha256']
        assert sha(Path(row['metadata']))==row['metadata_sha256']
        assert row['selected_engine']=='vm'
        if row['backend']=='decoded-threaded':assert row['vm_backend']=='decoded-threaded'
        if row['backend']=='portable-threaded':assert row['vm_backend']=='decoded-fallback'
        if row['backend']=='new-default':assert row['vm_backend']=='legacy'
        families[row['source'],row['family']].append(row)
    assert len(families)==63
    for rows in families.values():
        assert len(rows)==6 and len({r['backend'] for r in rows})==6
        assert len({r['vm_steps'] for r in rows})==1
    for row in report['failures']:
        outcomes={(r['code'],r['stderr']) for r in row['results']}
        assert len(row['results'])==6 and len(outcomes)==1 and next(iter(outcomes))[0]!=0
        assert sha(Path(row['metadata']))==row['metadata_sha256']
    assert len(report['failures'])==7
    result=dict(passed=True,reviewed_unix=time.time(),actual_C_files=378,sources=13,families=63,
                source_files=len(manifest['source_sha256']),root_rerun_contracts=native,
                CLI_error_contracts=7,effective_GNU_and_fallback_verified=True,
                machine_code_observation=manifest['machine_code_observation'],
                candidate_exe_sha256=manifest['executable_sha256']['candidate.exe'],
                evidence={path.relative_to(ROOT).as_posix():sha(path) for path in (manifest_path,report_path)},
                scope='All378 complete actualC files, all original source/harness/oracle/input/Metadata SHA,63 six-backend step groups,7 six-backend CLI errors and126 frozen inputs checked; root reran all5 frozen contracts including GNU934/fallback934/old404/old480+100k/ClangUBSan934. No performance/default/N10000 or universal-correctness claim; fullCTest final terminal checkpoint pending.')
    (ROOT/'outputs/stage2-root-vm-threaded-functional.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='root_rerun_contracts'}))


if __name__=='__main__':main()
