"""Offline proof audit preserving raw inputs, source hashes and verifier cost."""
import argparse,json,hashlib,sys
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.minor_bounds import contraction_bound,check_contraction_certificate
from isa_scheduler.evaluation import fingerprint


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',default='experiments/milestone-v10')
    parser.add_argument('--round',default='r59-minor-failure-audit');parser.add_argument('--budget-ms',type=float,default=100)
    args=parser.parse_args();source=Path(args.source);folder=ROOT/'experiments'/args.round
    folder.mkdir();report=json.loads((source/'report.json').read_text());records=[]
    failed={row['sha256']:row for row in report['records'] if row['variant']=='current_auto' and row['status'] in ('budget_exhausted','scheduling_failure')}
    inputs=[]
    for line in (source/'inputs.jsonl').read_text().splitlines():
        case=json.loads(line);data=case['input']
        if fingerprint(data) in failed:inputs.append(case)
    (folder/'inputs.jsonl').write_text('\n'.join(json.dumps(row,separators=(',',':'))for row in inputs)+'\n')
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in (ROOT/'isa_scheduler').glob('*.py')}
    start=perf_counter()
    for case in inputs:
        data=case['input'];key=fingerprint(data)
        for policy in ('degree','common'):
            certificate=contraction_bound(data,time_budget_ms=args.budget_ms,policy=policy)
            checked=perf_counter();verification=check_contraction_certificate(data,certificate);verify_ms=(perf_counter()-checked)*1000
            row={**failed[key], 'policy':policy,'certificate':certificate,'independent_verification':verification,'proof_verify_ms':verify_ms}
            records.append(row)
            print(json.dumps({k:row[k] for k in ('family','node_count','bit_width','status','policy','proof_verify_ms')}|verification),flush=True)
    result={'source':str(source),'source_report_sha256':hashlib.sha256((source/'report.json').read_bytes()).hexdigest(),
            'inputs_sha256':hashlib.sha256((folder/'inputs.jsonl').read_bytes()).hexdigest(),'source_manifest_at_start':manifest,
            'input_count':len(inputs),'independently_proven_inputs':len({r['sha256']for r in records if r['independent_verification']['infeasible_under_identity_model']}),
            'elapsed_seconds':perf_counter()-start,'budget_ms_per_policy':args.budget_ms,
            'scope':'offline distinct-original-identity COPY-only proof; not online timings, runnable witness, or global official unsatisfiability',
            'records':records}
    (folder/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('records','source_manifest_at_start')}))


if __name__=='__main__':main()
