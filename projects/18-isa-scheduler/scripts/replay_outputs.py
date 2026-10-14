"""Re-read saved strict outputs and independently check them without scheduling."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.evaluation import fingerprint
from isa_scheduler.verify import IntegerSemantics,interpret,verify


def main():
    parser=argparse.ArgumentParser();parser.add_argument('directory');args=parser.parse_args()
    folder=Path(args.directory);started=perf_counter()
    original={fingerprint(case['input']):case['input'] for case in map(json.loads,(folder/'inputs.jsonl').read_text(encoding='utf-8').splitlines())}
    report=json.loads((folder/'report.json').read_text(encoding='utf-8'))
    if hashlib.sha256((folder/'inputs.jsonl').read_bytes()).hexdigest()!=report['corpus_sha256']:
        raise ValueError('Input corpus hash mismatch')
    expected={(r['sha256'],r['variant']):r.get('output_sha256')for r in report['records']if r['status']=='verified'}
    after=report['paired_variants']['after'];seen=set();records=[]
    for line_number,line in enumerate((folder/'optimized_outputs.jsonl').read_text(encoding='utf-8').splitlines(),start=1):
        row={'line':line_number,'status':'started'}
        try:
            saved=json.loads(line);key=(saved['input_sha256'],saved['variant'])
            if key in seen or key[1]!=after:raise ValueError('Duplicate/wrong-variant output')
            seen.add(key)
            data=original[key[0]];output=saved['output'];output_hash=fingerprint(output)
            if key not in expected or expected[key]!=output_hash:raise ValueError('Saved output hash/identity mismatch')
            verify(data,output)
            names=sorted({r['reg']for r in data['instructions']if r['op']=='GET'})
            inputs={name:-17+i*11 for i,name in enumerate(names)}
            for semantics in (IntegerSemantics(8,True),IntegerSemantics(16,False),IntegerSemantics(32,True)):
                if interpret(data['instructions'],inputs,semantics)!=interpret(output['optimized_instructions'],inputs,semantics):
                    raise ValueError('Independent replay numeric mismatch')
            row.update(status='verified',input_sha256=key[0],variant=key[1],output_sha256=output_hash,numeric_configurations=3)
        except Exception as exc:row.update(status='verification_failure',exception_type=type(exc).__name__,error=str(exc))
        records.append(row)
    missing=[key for key in expected if key[1]==after and key not in seen]
    replay={'method':'fresh serialized input/output; no scheduler call or internal state; alternate signed inputs',
            'attempted':len(records),'verified':sum(r['status']=='verified'for r in records),
            'missing_success_outputs':len(missing),
            'elapsed_seconds':perf_counter()-started,'records':records}
    (folder/'serialized-replay.json').write_text(json.dumps(replay,indent=2)+'\n')
    print(json.dumps({k:v for k,v in replay.items()if k!='records'}))
    return 4 if replay['verified']!=replay['attempted'] or missing else 0


if __name__=='__main__':raise SystemExit(main())
