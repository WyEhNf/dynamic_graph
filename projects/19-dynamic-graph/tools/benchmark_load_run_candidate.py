"""Selected DEV matched CLI experiment, same immutable binary, no promotion.

Three sources selected AFTER the small dispatch profile, not a holdout. Compare
unfused threaded vs run4 in this binary; NOT run4 vs old pair performance.
Five alternating pairs, full original-C streams and failure costs retained.
"""
import json
from pathlib import Path
import statistics
import subprocess
from time import perf_counter
from profile_vm_dispatch import file_sha

BASE=Path('G:/Hackathon-stage2-artifacts/project19/load-run4')
OUT=BASE/'selected-performance3'
EXE=BASE/'build/cholesky_runtime.exe'
PLAN=Path('G:/Hackathon-stage2-artifacts/project19/load-pair/next-static-plan/plan.json')
NAMES=['generic-if-while','fresh-carry-fma-plain','nested-gram-three-dense']


def main():
    OUT.mkdir(exist_ok=False)
    plan=json.loads(PLAN.read_text());cases={c['source']:c for c in plan['functional']['cases']}
    report={'completed':False,'records':[],'summary':[],
        'declaration':{'sources':NAMES,'pairs':5,'order':'alternate unfused/run4 and run4/unfused',
            'dataset':'adaptive selected previously used DEV streams, not holdout',
            'comparison':'same EXE unfused decoded-threaded versus run4; not old pair versus run4',
            'all_outputs':'whole stream exact original-C bytes, failures retained',
            'timing':'process wall includes startup/metadata/input/execution/output; hash comparison separately timed',
            'default_changed':False},'exe_sha256':file_sha(EXE),'tool_sha256':file_sha(Path(__file__))}
    began=perf_counter()
    def persist(): (OUT/'partial.json').write_text(json.dumps(report,indent=2))
    for name in NAMES:
        c=cases[name]
        assert all(file_sha(c['paths'][k])==c['hashes'][k] for k in ['source.c','program.meta','input.bin','oracle.bin'])
        common=c['runtime_command_common'].copy();common[0]=str(EXE)
        common[common.index('--engine')+1]='vm'
        for phase in range(-1,5):
            order=['decoded-threaded','decoded-threaded-load-pair']
            if phase>=0 and phase%2:order.reverse()
            for backend in order:
                label=f'{name}-phase{phase}-{backend}';output=OUT/f'{label}.bin'
                command=common+['--output',str(output),'--vm-backend',backend]
                row={'source':name,'phase':phase,'warmup':phase<0,'backend':backend,'command':command}
                report['records'].append(row);tick=perf_counter()
                try:
                    p=subprocess.run(command,capture_output=True,text=True,timeout=60)
                    row.update(process_wall_seconds=perf_counter()-tick,exit_code=p.returncode)
                    (OUT/f'{label}.stdout').write_text(p.stdout);(OUT/f'{label}.stderr').write_text(p.stderr)
                    p.check_returncode();row['cli_metrics']=json.loads(p.stdout)
                    assert row['cli_metrics']['vm_steps']==c['expected_vm_steps']
                    compare=perf_counter();row['output_sha256']=file_sha(output)
                    assert row['output_sha256']==c['hashes']['oracle.bin']
                    assert output.stat().st_size==c['reference_bytes']
                    row['full_original_C_comparison_seconds']=perf_counter()-compare;row['passed']=True
                except BaseException as error:
                    row.update(passed=False,error=str(error),failed_elapsed_seconds=perf_counter()-tick);persist();raise
                persist()
        pairs=[]
        for phase in range(5):
            r={x['backend']:x for x in report['records'] if x['source']==name and x['phase']==phase}
            pairs.append(r['decoded-threaded-load-pair']['process_wall_seconds']/r['decoded-threaded']['process_wall_seconds'])
        report['summary'].append({'source':name,'wall_ratio_pairs':pairs,'wall_ratio_median':statistics.median(pairs),
            'wins':sum(x<1 for x in pairs),'losses':sum(x>1 for x in pairs),'scope':'selected five-pair whole-process comparison only'})
        persist();print(json.dumps(report['summary'][-1]),flush=True)
    report.update(completed=True,passed=True,wall_seconds=perf_counter()-began)
    (OUT/'report.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
