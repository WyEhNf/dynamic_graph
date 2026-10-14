"""One paired milestone for an isolated edit-indexing candidate."""
import hashlib
import json
import statistics
import time
from pathlib import Path

from context_governance.core import ByteEstimate, Item, govern
from context_governance.typescript_context import TypeScriptContext


def identity(result):
    return {k:result[k] for k in ['items','dependencies','warnings','conservative_full_project_fallback','compiler_version']}


def selected(result):
    items=[Item('task','requirement','Preserve run and its dependencies.',True),*result['items']]
    return govern('Preserve run and its dependencies.',items,1500,ByteEstimate(),result['dependencies'])


def main():
    root=Path(__file__).resolve().parents[1]
    folder=root/'adapters/typescript/research-candidates-v18'
    workers={name:TypeScriptContext(worker_path=folder/file) for name,file in
             [('baseline','baseline.mjs'),('incremental','incremental.mjs')]}
    started=time.time()
    report={'started_unix':started,'origin':'Synthetic TypeScript edit indexing; no model generation',
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'worker_sha256':{name:hashlib.sha256((folder/file).read_bytes()).hexdigest() for name,file in
                             [('baseline','baseline.mjs'),('incremental','incremental.mjs')]},
            'scope':'Alternating paired worker IPC+index+governance wall time after an untimed prior snapshot. Cache disabled for every request; reuse is of unchanged compiler SourceFiles, not complete analysis results. Node RSS is a point observation, not process peak. ByteEstimate budgets are not model tokens.',
            'semantic_edits':[],'performance':[]}
    try:
        files={'main.ts':'import type {Payload} from "./types"; export function run(x:Payload){return x.x;}',
               'types.ts':'export interface A{x:number}; export interface B{x:number}; export interface Payload extends A {}'}
        changes=[(dict(files),['main.ts'])]
        for index in range(12):
            variant=dict(files)
            variant['types.ts']=variant['types.ts'].replace('extends A','extends B') if index%2 else variant['types.ts']
            if index in [2,3]:
                variant['main.ts']='import type {Payload} from "./new"; export function run(x:Payload){return x.x;}'
                if index==3: variant['new.ts']='export interface Payload{x:number}'
            if index in [4,5]: variant['types.ts']+='\nexport let runtime=1; runtime+=2;'
            if index==6: variant['types.ts']='export interface Payload { broken'
            if index==7: variant['plugin.ets']='struct Card { build() {} }'
            if index==8: variant['main.ts']='const m=import("./types"); export function run(x:number){return x;}'
            if index==9: variant['global.ts']='let GLOBAL=2; GLOBAL+=3;'
            if index==10: variant['empty.ts']='// 👩‍💻 中文\r\n'
            changes.append((variant,['main.ts','types.ts'] if index==11 else ['main.ts']))
        for index,(snapshot,pins) in enumerate(changes+list(reversed(changes))):
            results={name:worker.analyze(snapshot,pins,use_cache=False) for name,worker in workers.items()}
            if identity(results['baseline'])!=identity(results['incremental']):
                raise AssertionError(f'Compiler reuse changed graph/source at edit {index}')
            left=selected(results['baseline']);right=selected(results['incremental'])
            if (left['context'],left['decisions'],left['dependency_map']) != (right['context'],right['decisions'],right['dependency_map']):
                raise AssertionError(f'Compiler reuse changed governance at edit {index}')
            report['semantic_edits'].append({'index':index,'source_sha256':hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest(),'equivalent':True})
        for count in [128,512,2048,8192]:
            for parts in [1,8]:
                files={'main.ts':'import {twice} from "./helper"; export function run(x:number){return twice(x);}',
                       'helper.ts':'export function twice(x:number){return x*2;}'}
                for part in range(parts):
                    files[f'unrelated{part}.ts']=''.join(f'export function unused_{i}(x:number){{return x+{i};}}\n' for i in range(part,count,parts))
                samples={name:[] for name in workers}
                maximum_rss={name:0 for name in workers}
                for repeat in range(11):
                    before=dict(files);before['helper.ts']=before['helper.ts'].replace('x*2',f'x*{repeat+2}')
                    after=dict(files);after['helper.ts']=after['helper.ts'].replace('x*2',f'x*{repeat+3}')
                    for worker in workers.values(): worker.analyze(before,['main.ts'],use_cache=False)
                    results={};selections={}
                    order=['baseline','incremental'] if repeat%2==0 else ['incremental','baseline']
                    for name in order:
                        tick=time.perf_counter_ns()
                        results[name]=workers[name].analyze(after,['main.ts'],use_cache=False)
                        selections[name]=selected(results[name])
                        elapsed=(time.perf_counter_ns()-tick)/1e6
                        samples[name].append({'wall_ms':elapsed,'worker_analysis_ms':results[name]['analysis_ms'],'cache_hit':results[name]['cache_hit']})
                        maximum_rss[name]=max(maximum_rss[name],results[name]['worker_resident_bytes'])
                    if identity(results['baseline'])!=identity(results['incremental']):raise AssertionError('Edited compiler graph changed')
                    if selections['baseline']!=selections['incremental']:
                        # Timed governance contains its own measured metrics.
                        for name in selections: selections[name].pop('metrics',None)
                        if selections['baseline']!=selections['incremental']:raise AssertionError('Edited governance changed')
                medians={name:statistics.median(x['wall_ms'] for x in group) for name,group in samples.items()}
                record={'declarations':count,'files':parts,'source_sha256':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),
                        'samples':samples,'wall_median_ms':medians,'speedup':medians['baseline']/medians['incremental'],
                        'maximum_observed_rss_bytes':maximum_rss,'all_11_edits_equivalent':True}
                report['performance'].append(record)
                print(json.dumps({k:record[k] for k in ['declarations','files','wall_median_ms','speedup']}),flush=True)
    finally:
        for worker in workers.values():worker.close()
    report['wall_seconds']=time.time()-started
    report['median_speedup']=statistics.median(x['speedup'] for x in report['performance'])
    report['minimum_speedup']=min(x['speedup'] for x in report['performance'])
    (root/'artifacts/typescript-incremental-v18.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=lambda x:x.__dict__),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['wall_seconds','median_speedup','minimum_speedup']}))


if __name__=='__main__':main()
