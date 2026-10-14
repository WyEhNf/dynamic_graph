"""Replay strict outputs with untrusted original-permutation sidecar proof."""
import argparse,hashlib,json,sys
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from isa_scheduler.evaluation import fingerprint
from isa_scheduler.identity_witness import check_identity_witness
from isa_scheduler.verify import verify


def main():
    parser=argparse.ArgumentParser();parser.add_argument('source');args=parser.parse_args();folder=Path(args.source)
    inputs={fingerprint(case['input']):case['input']for case in map(json.loads,(folder/'inputs.jsonl').read_text().splitlines())}
    orders={(row['input_sha256'],row['variant']):row['original_order']for row in map(json.loads,(folder/'original_orders.jsonl').read_text().splitlines())}
    start=perf_counter();records=[]
    for saved in map(json.loads,(folder/'optimized_outputs.jsonl').read_text().splitlines()):
        key=(saved['input_sha256'],saved['variant']);data=inputs[key[0]];output=saved['output'];verify(data,output)
        proof=check_identity_witness(data,output,orders[key])
        records.append({'input_sha256':key[0],'variant':key[1],'output_sha256':fingerprint(output),'independent_symbolic_verified':True,'independent_identity_proof':proof})
    report={'source':str(folder),'attempted':len(records),'verified_identity_outputs':len(records),'elapsed_s':perf_counter()-start,
            'input_file_sha256':hashlib.sha256((folder/'inputs.jsonl').read_bytes()).hexdigest(),
            'output_file_sha256':hashlib.sha256((folder/'optimized_outputs.jsonl').read_bytes()).hexdigest(),
            'order_witness_file_sha256':hashlib.sha256((folder/'original_orders.jsonl').read_bytes()).hexdigest(),
            'checker_manifest':{name:hashlib.sha256((ROOT/'isa_scheduler'/name).read_bytes()).hexdigest()for name in ('identity_witness.py','raw_pure.py','verify.py')},
            'method':'raw input/output and untrusted complete permutation; no scheduler or DAG model state; symbolic and exact identity purposes separate','records':records}
    (folder/'identity-replay.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({key:value for key,value in report.items()if key!='records'}))


if __name__=='__main__':main()
