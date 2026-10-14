"""Full API recovery, original ID/plan preservation and every failure cost."""
from pathlib import Path
import hashlib,json,subprocess,time

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('G:/Hackathon-stage2-artifacts/project27/20261013/r63/api');OUT.mkdir(parents=True,exist_ok=True)
BASE=Path('G:/Hackathon-stage2-artifacts/project27/20261013/baseline/aicore_bench.exe')
NEW=OUT.parent/'aicore_bench.exe'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    report={'complete':False,'results':{},'compile_flags':'both standalone GCC 15.2 -std=c++17 -O2 -I include',
            'timing_scope':'one functional comparison in shared host load; includes all failures; not stable speedup evidence',
            'sha256':{str(p):sha(p) for p in [BASE,NEW,ROOT/'research/batch51/solution.cpp',ROOT/'research/batch63/single-file-solution.cpp',Path(__file__)]}}
    for label,relative,order in [('hard202','data/hard-corpus-resumed.json',['before','after']),('held48','data/projection-retention-heldout-batch45.json',['after','before'])]:
        src=ROOT/relative;data=json.loads(src.read_text());rows={};started=time.perf_counter();report['sha256'][str(src)]=sha(src)
        for side in order:
            dst=OUT/f'{label}-{side}.json';errors=OUT/f'{label}-{side}-failures.json'
            process=subprocess.run([str(BASE if side=='before' else NEW),'--input',str(src),'--output',str(dst),'--failures',str(errors)],capture_output=True,text=True)
            assert process.returncode in (0,1),(side,process.stdout,process.stderr)
            doc=json.loads(dst.read_text());assert len(doc['cases'])==len(data['cases']);rows[side]=doc['cases']
            report['sha256'][str(dst)]=sha(dst);report['sha256'][str(errors)]=sha(errors)
        recovered=[];common=0
        for case,b,a in zip(data['cases'],rows['before'],rows['after']):
            assert case['name']==b['name']==a['name'];assert b['models_equal'] and a['models_equal']
            if b['pass']:
                assert a['pass'] and b['plan']==a['plan'] and b['T']==a['T'] and b['peak_memory']==a['peak_memory'];common+=1
            elif a['pass']:
                assert a['valid'] and a['T']<=a['deadline_us'];ids=[task['op_id'] for stream in a['plan']['streams'] for task in stream['tasks']]
                assert len(ids)==len(set(ids))==len(case['nodes']) and set(ids)=={n['id'] for n in case['nodes']};recovered.append(a['name'])
        costs={}
        for side in ('before','after'):
            rs=rows[side];costs[side]={'cpu_us':sum(x['solve_thread_cpu_us'] for x in rs),'wall_us':sum(x['solve_us'] for x in rs),
                'max_wall_us':max(x['solve_us'] for x in rs),'passed':sum(x['pass'] for x in rs),'failed':sum(not x['pass'] for x in rs),
                'old_failed_cpu_us':sum(x['solve_thread_cpu_us'] for x,b in zip(rs,rows['before']) if not b['pass']),
                'old_failed_wall_us':sum(x['solve_us'] for x,b in zip(rs,rows['before']) if not b['pass'])}
        report['results'][label]={'total':len(data['cases']),'original_pass_plans_identical':common,'recovered':recovered,'costs':costs,'elapsed_wall':time.perf_counter()-started}
        (OUT/'report.partial.json').write_text(json.dumps(report,indent=2));print(json.dumps(report['results'][label]),flush=True)
    report['complete']=True;(OUT/'report.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
