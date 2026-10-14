"""Static original-identity COPY attribution from already verified outputs."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def describe(saved, start, stop):
    history=[]; cursor=0; traces=[]; births={}
    for position,row in enumerate(saved['output']['optimized_instructions']):
        if row['op']=='COPY':
            source=position-int(row['source'][2:]); identity=history[source]
            if start<=cursor<=stop:
                traces.append({'physical_slot':position,'original_cursor':cursor,
                    'identity':identity,'distance':int(row['source'][2:])})
        else:
            identity=saved['original_order'][cursor]; cursor+=1; births[identity]=position
            if row['op']=='SET': identity=None
        history.append(identity)
    return {'local_copy_count':len(traces),'local_copy_identities':dict(Counter(t['identity'] for t in traces)),
            'local_copy_traces':traces,'full_copy_count':sum(row['op']=='COPY' for row in saved['output']['optimized_instructions']),
            'original_birth_slots':{str(identity):births[identity] for identity in (17,21,37,55,57,59,60,61)}}


def main():
    folder=ROOT/'experiments/r162-tree-pair-mechanism'; folder.mkdir(exist_ok=False)
    source=ROOT/'experiments/r158-tree-fixed-pair-diagnostic'
    row=next(r for r in json.loads((source/'report.json').read_text())['records'] if r['family']=='ragged_tree' and r['parent']==59)
    key=row['input_sha256']; paths=list(source.glob(key[:16]+'-parent59-outlet*-output.json'))
    winner=min(paths,key=lambda p:json.loads(p.read_text())['copies'])
    controls=ROOT/'experiments/r161-tree-pair-serial-controls'
    files={'serialAB':controls/(key[:16]+'-parent59-serial0-output.json'),
           'serialBA':controls/(key[:16]+'-parent59-serial1-output.json'),
           'interleave':winner}
    start,stop=row['stats']['rank_interval']
    result={'input_sha256':key,'parent':59,'local_original_interval':[start,stop],
        'external_roles':row['stats']['external_roles'],'external_ages':row['stats']['external_ages'],
        'details':{name:describe(json.loads(path.read_text()),start,stop) for name,path in files.items()},
        'evidence_source_sha256':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in files.values()},
        'scope':'Static attribution of actual already verified complete outputs; no new emitter/solver/gold/quality-corpus run. Each output keeps all64 originals.'}
    (folder/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    p=folder/'report.json'; (folder/'evidence-provenance.json').write_text(json.dumps({'frozen_utc':datetime.now(timezone.utc).isoformat(),
        'evidence_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()},
        'source_sha256':{str(Path(__file__).relative_to(ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}},indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__': main()
