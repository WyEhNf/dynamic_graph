"""Collect actual code-quality and all-attempt inference cost evidence."""
import hashlib
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[1]
ART=Path('G:/Hackathon-stage2-artifacts/project11')
NAMES=['qwen3-nonthinking-dev-paired-20261013','qwen3-bounded-dev-paired-20261013',
       'qwen3-singlepass-dev-paired-20261013','qwen3-singlepass-holdout-paired-20261013']


def main():
    report={'created_unix':time.time(),'experiments':[],
        'scope':'Actual local finite tests. Scores are per experiment; no merging DEV and held cases or uncompleted attempts.',
        'timing_scope':'ttft_ms includes tokenization, transfer, prefill and the first token. Per-segment remaining_ms is elapsed_ms minus ttft_ms, through final GPU synchronization; text conversion happens afterward. generation_callback_seconds includes evidence conversion and writing. workflow_seconds additionally includes prompt building and public checks. These are not pure GPU kernel profiles; other project work was concurrent.'}
    for name in NAMES:
        directory=ART/name
        path=directory/'report.json'
        if not path.exists(): continue
        data=json.loads(path.read_text(encoding='utf-8'))
        score_path=directory/'held-score.json'
        scores=json.loads(score_path.read_text(encoding='utf-8')) if score_path.exists() else None
        scoring={(r['id'],r['mode']):r for r in scores['rows']} if scores else {}
        rows=[]
        for case in data['cases']:
            attempts=case['search']['attempts']; gens=[a['generation'] for a in attempts]
            held=scoring.get((case['id'],case['mode']),{})
            phases=[]
            for index,g in enumerate(gens):
                for phase_index,s in enumerate(g.get('segments',[g])):
                    phases.append({'candidate':index,'phase':phase_index,'input_tokens':s['input_tokens'],
                        'output_tokens':s['output_tokens'],'ttft_ms':s['ttft_ms'],
                        'remaining_ms':s['elapsed_ms']-s['ttft_ms'],'elapsed_ms':s['elapsed_ms'],
                        'stopped_on_eos':s.get('stopped_on_eos')})
            rows.append({'id':case['id'],'mode':case['mode'],'attempts':len(attempts),
                'selected':case['search']['selected'],'public_pass':case['search']['selected'] is not None,
                'initial_held_pass':held.get('initial_passed'),'selected_held_pass':held.get('selected_passed'),
                'cumulative_input_tokens':sum(g['input_tokens'] for g in gens),
                'cumulative_output_tokens':sum(g['output_tokens'] for g in gens),
                'generation_seconds':sum(g['elapsed_ms'] for g in gens)/1000,
                'generation_callback_seconds':sum(a.get('generation_seconds',0) for a in attempts),
                'workflow_seconds':case.get('workflow_seconds'),
                'initial_input_tokens':phases[0]['input_tokens'],
                'initial_ttft_ms':gens[0]['ttft_ms'],
                'initial_context_overhead_ms':case.get('request_context_overhead_ms'),
                'forced_boundaries':sum(bool(g.get('forced_reasoning_end')) for g in gens),'phases':phases})
        paired=[]
        for case_id in sorted({r['id'] for r in rows}):
            modes={r['mode']:r for r in rows if r['id']==case_id}
            if set(modes)!={'full','compressed'}: continue
            full,comp=modes['full'],modes['compressed']
            paired.append({'id':case_id,
                'cumulative_input_reduction':1-comp['cumulative_input_tokens']/full['cumulative_input_tokens'],
                'initial_input_reduction':1-comp['initial_input_tokens']/full['initial_input_tokens'],
                'initial_ttft_reduction':1-comp['initial_ttft_ms']/full['initial_ttft_ms'],
                'all_attempt_generation_reduction':1-comp['generation_seconds']/full['generation_seconds'],
                'full_selected_held_pass':full['selected_held_pass'],'compressed_selected_held_pass':comp['selected_held_pass']})
        report['experiments'].append({'name':name,'completed':data['completed'],'declaration':data['declaration'],
            'report_path':str(path),'report_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'held_score_path':str(score_path) if scores else None,
            'held_score_sha256':hashlib.sha256(score_path.read_bytes()).hexdigest() if scores else None,
            'load_seconds':data.get('load_seconds'),'wall_seconds':data['wall_seconds'],
            'gpu_peak_allocated_bytes':data.get('gpu_peak_allocated_bytes'),'rows':rows,'paired':paired})
    report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted((ROOT/'src/context_governance').glob('*.py'))}
    output=ROOT/'artifacts/optimization-20261013.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(str(output))


if __name__=='__main__':main()
