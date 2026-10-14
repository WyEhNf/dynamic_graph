"""Fresh serialized output and global COPY certificate audit; no scheduling."""
import argparse,json,sys,hashlib
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.evaluation import fingerprint
from isa_scheduler.model import parse_block
from isa_scheduler.spine_copy_bound import spine_copy_bound,check_spine_copy_certificate
from isa_scheduler.consumer_copy_bound import consumer_copy_bound,check_consumer_copy_certificate
from isa_scheduler.pair_copy_bound import pair_copy_bound,check_pair_copy_certificate
from isa_scheduler.verify import verify


def main():
    parser=argparse.ArgumentParser();parser.add_argument('source');args=parser.parse_args();folder=Path(args.source)
    inputs={fingerprint(case['input']):case['input']for case in map(json.loads,(folder/'inputs.jsonl').read_text().splitlines())}
    start=perf_counter();records=[]
    with (folder/'optimized_outputs.jsonl').open() as stream:
        for line in stream:
            serialized=json.loads(line);data=inputs[serialized['input_sha256']];output=serialized['output']
            verify(data,output)
            block=parse_block(data)
            candidates=[candidate for candidate in (spine_copy_bound(block),consumer_copy_bound(block),pair_copy_bound(block))if candidate is not None]
            certificate=max(candidates,key=lambda candidate:candidate['copy_lower_bound'])if candidates else None;proof=None
            copies=sum(row['op']=='COPY' for row in output['optimized_instructions'])
            if certificate is not None:
                checker={'distinct_consumer_identity_relay_sum':check_consumer_copy_certificate,'disjoint_terminal_root_pairs_age_sum':check_pair_copy_certificate}.get(certificate['kind'],check_spine_copy_certificate)
                proof=checker(data,certificate)
                if proof['verified_global_copy_lower_bound']>copies:raise ValueError('Global bound contradicted')
            relative=(copies-proof['verified_global_copy_lower_bound'])/copies if proof and copies else None
            records.append({'input_sha256':serialized['input_sha256'],'output_sha256':fingerprint(output),
                            'raw_symbolic_verified':True,'certificate':certificate,'independent_proof':proof,
                            'copies':copies,'maximum_relative_copy_reduction':relative,
                            'within_explicit_half_percent_tolerance':relative is not None and relative<=.005})
    report={'source':str(folder),'attempted':len(records),'verified_outputs':len(records),'elapsed_s':perf_counter()-start,
            'proofs_checked':sum(row['independent_proof'] is not None for row in records),
            'within_explicit_half_percent_tolerance':sum(row['within_explicit_half_percent_tolerance'] for row in records),
            'output_file_sha256':hashlib.sha256((folder/'optimized_outputs.jsonl').read_bytes()).hexdigest(),
            'checker_sha256':hashlib.sha256((ROOT/'isa_scheduler/spine_copy_bound.py').read_bytes()).hexdigest(),
            'proof_source_manifest':{name:hashlib.sha256((ROOT/'isa_scheduler'/name).read_bytes()).hexdigest()for name in ('spine_copy_bound.py','consumer_copy_bound.py','pair_copy_bound.py','raw_pure.py','verify.py')},
            'method':'raw serialized outputs independent symbolic check; bound proposal only uses parsed input; separate raw-JSON proof checker reconstructs forced spine, distinct consumers or disjoint terminal root pairs; no scheduler invocation',
            'records':records}
    (folder/'quality-bound-replay.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k!='records'}))


if __name__=='__main__':main()
