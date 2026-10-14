"""Paired independent raw-JSON COPY proof check cost, excluding scheduling/IO."""
import argparse,json,sys,hashlib,statistics
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from experiments.baseline_r70.isa_scheduler.spine_copy_bound import check_spine_copy_certificate as old_check
from isa_scheduler.spine_copy_bound import check_spine_copy_certificate,spine_copy_bound
from isa_scheduler.model import parse_block


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',default='experiments/r67-spine-bound-stop');parser.add_argument('--round',default='r72-proof-check-cost');parser.add_argument('--repeats',type=int,default=3)
    args=parser.parse_args();source=Path(args.source);folder=ROOT/'experiments'/args.round;folder.mkdir()
    corpus=source/'inputs.jsonl';data=[item.get('input',item)for item in map(json.loads,corpus.read_text().splitlines())]
    proofs=[spine_copy_bound(parse_block(item))for item in data];records=[];start=perf_counter()
    manifests={'current':hashlib.sha256((ROOT/'isa_scheduler/spine_copy_bound.py').read_bytes()).hexdigest(),
               'frozen':hashlib.sha256((ROOT/'experiments/baseline_r70/isa_scheduler/spine_copy_bound.py').read_bytes()).hexdigest()}
    for index,(item,proof) in enumerate(zip(data,proofs)):
        timings={'frozen':[],'current':[]};expected=None
        for repeat in range(args.repeats):
            functions=(('frozen',old_check),('current',check_spine_copy_certificate))
            if repeat%2:functions=functions[::-1]
            for label,function in functions:
                tick=perf_counter();checked=function(item,proof);elapsed=(perf_counter()-tick)*1000
                if expected is None:expected=checked
                if checked!=expected:raise ValueError('Independent proof check result mismatch')
                timings[label].append(elapsed)
        medians={label:statistics.median(values)for label,values in timings.items()}
        records.append({'case':index,'nodes':len(item['instructions']),'bit_width':item['bit_width'],'timings_ms':timings,'medians_ms':medians,'speedup':medians['frozen']/medians['current'],'verified_proof':expected})
    report={'case_count':len(records),'repeats':args.repeats,'elapsed_s':perf_counter()-start,
            'source':str(source),'source_corpus_sha256':hashlib.sha256(corpus.read_bytes()).hexdigest(),'checker_sha256':manifests,
            'median_speedup':statistics.median(row['speedup']for row in records),'method':'alternating raw JSON proof-only check; matching necessary bound; no scheduling or IO in timed sections; never substitutes output correctness verification',
            'records':records}
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='records'}))


if __name__=='__main__':main()
