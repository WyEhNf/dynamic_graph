"""Fresh original-C byte/step/PC validation, first small matrix of all19 sources.

Observer timings are functionality diagnostics and are not performance results.
"""
import json
from pathlib import Path
import struct
import subprocess
from time import perf_counter
from profile_vm_dispatch import file_sha, matrix_at

OUT=Path('G:/Hackathon-stage2-artifacts/project19/load-run4/functional19')
PLAN=Path('G:/Hackathon-stage2-artifacts/project19/load-pair/next-static-plan/plan.json')
OBSERVER=OUT.parent/'observer.exe'


def main():
    OUT.mkdir(exist_ok=False);began=perf_counter()
    plan=json.loads(PLAN.read_text());unique={}
    for c in plan['functional']['cases']:unique.setdefault(c['hashes']['source.c'],c)
    assert len(unique)==19
    report={'records':[],'completed':False,'scope':'Previously used first small original-C matrices, full byte comparison; no speedup or large-shape claim',
        'plan_sha256':file_sha(PLAN),'observer_sha256':file_sha(OBSERVER),
        'core_sha256':file_sha(OUT.parent/'build/libcholesky_core.a'),'validator_sha256':file_sha(Path(__file__))}
    for index,c in enumerate(unique.values()):
        hashes={name:file_sha(c['paths'][name]) for name in ['source.c','program.meta','input.bin','oracle.bin']}
        assert all(value==c['hashes'][name] for name,value in hashes.items())
        n,payload=matrix_at(c['paths']['input.bin'],0);ng,expected=matrix_at(c['paths']['oracle.bin'],0)
        assert n==ng
        header=struct.pack('<II',1,n);input_path=OUT/f'{index}-input.bin'
        input_path.write_bytes(header+payload);rows=[]
        for backend in ['decoded-threaded','decoded-threaded-load-pair']:
            output=OUT/f'{index}-{backend}.bin'
            command=[str(OBSERVER),c['paths']['program.meta'],str(input_path),str(output),backend,'vm',str(c['block']),'1','serial']
            p=subprocess.run(command,capture_output=True,text=True,check=True,timeout=30)
            (OUT/f'{index}-{backend}.stdout').write_text(p.stdout)
            (OUT/f'{index}-{backend}.stderr').write_text(p.stderr)
            messages=[json.loads(line) for line in p.stdout.splitlines()];assert len(messages)==2
            row=messages[0];assert not row['error'] and row['n']==n and row['engine']=='vm'
            assert row['vm_budget_work']==row['vm_budget_proof_ms']==0
            assert output.read_bytes()==header+expected
            rows.append({'backend':backend,'metrics':row,'output_sha256':file_sha(output),'command':command})
        a,b=[r['metrics'] for r in rows]
        assert all(a[k]==b[k] for k in ['vm_steps','vm_last_pc','error','engine','vm_effective_step_limit','n'])
        report['records'].append({'source':c['source'],'matrix_index':0,'n':n,'full_original_file_sha256':hashes,
            'original_C_bytes_equal':True,'paired_steps_pc_equal':True,'runs':rows})
        (OUT/'partial.json').write_text(json.dumps(report,indent=2))
    report.update(completed=True,passed=True,sources=len(report['records']),wall_seconds=perf_counter()-began,
        removed_dispatches=sum(r['runs'][1]['metrics']['vm_fusion_pairs_executed'] for r in report['records']))
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ['passed','sources','removed_dispatches','wall_seconds']}))


if __name__=='__main__':main()
