"""Post-generation scoring, never imported by the generation process."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from context_governance.bundles import load_case
from context_governance.quality import check_code


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('report'); args=parser.parse_args()
    path=Path(args.report); report=json.loads(path.read_text(encoding='utf-8'))
    if not report['completed']: raise ValueError('generation batch must be complete before scoring')
    suite=ROOT/report['declaration']['suite']
    result={'generation_report_sha256':sha(path),'generation_report':str(path),
            'scoring_script_sha256':sha(__file__),'started_unix':time.time(),
            'scope':'Finite independently held test execution after all generation; no full-domain proof',
            'rows':[]}
    for row in report['cases']:
        metadata,snapshot,_,_=load_case(suite,row['id'])
        if metadata['snapshot_sha256']!=row['snapshot_sha256']: raise ValueError('snapshot changed')
        checks=[]; test=suite/'tests'/f"{row['id']}.py"
        for attempt in row['search']['attempts']:
            generated=attempt['generation']
            checked=({'passed':False,'reason':generated['protocol_error']} if generated.get('protocol_error')
                else check_code(generated['final_output'],snapshot,metadata['target_file'],test))
            checks.append({'index':attempt['index'],'public_pass':attempt['public_check']['passed'],
                           'held_check':checked})
        chosen=row['search']['selected']
        result['rows'].append({'id':row['id'],'mode':row['mode'],'tests_sha256':sha(test),
            'selected':chosen,'selected_passed':bool(chosen is not None and checks[chosen]['held_check']['passed']),
            'initial_passed':checks[0]['held_check']['passed'],'attempts':checks})
    result['initial_passes']=sum(r['initial_passed'] for r in result['rows'])
    result['selected_passes']=sum(r['selected_passed'] for r in result['rows'])
    with (path.parent/'held-score.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps({key:result[key] for key in ('initial_passes','selected_passes')}))


if __name__=='__main__':main()
