"""Freeze equal-work streams for short VM programs; no new numeric oracle.

Repeat each complete original input stream and corresponding original-C output
stream equally, preserving all matrix bytes. Execution resets scalar state at
every matrix. This is timing amplification, not new source/shape coverage.
"""
import hashlib
import json
import math
from pathlib import Path
import struct

BASE=Path('G:/Hackathon-stage2-artifacts/project19/20261013-bounded-stack')
SOURCE=Path('G:/Hackathon-stage2-artifacts/project19/load-pair/next-static-plan/plan.json')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def main():
    dest=BASE/'amplified-plan';dest.mkdir(exist_ok=False)
    plan=json.loads(SOURCE.read_text());cases=plan['functional']['cases']
    for index,c in enumerate(cases):
        count=c['matrices'];steps=c['expected_vm_steps']
        repeats=max(1,math.ceil(40000000/steps)) if c['kind']=='vm' else 1
        if repeats==1:continue
        for name in ['input.bin','oracle.bin']:
            origin=Path(c['paths'][name]);assert sha(origin)==c['hashes'][name]
            raw=origin.read_bytes();assert struct.unpack('<I',raw[:4])[0]==count
            target=dest/f'{index}-{name}'
            with target.open('xb') as out:
                out.write(struct.pack('<I',count*repeats))
                for _ in range(repeats):out.write(raw[4:])
            c['paths'][name]=str(target);c['hashes'][name]=sha(target)
        c['amplification']={'repeats':repeats,'source_plan_sha256':sha(SOURCE),'original_matrix_count':count,
            'meaning':'identical full original-C matrix pairs repeated; no new source or shape'}
        c['matrices']*=repeats;c['expected_vm_steps']*=repeats
        c['input_matrix_headers']*=repeats;c['reference_bytes']=Path(c['paths']['oracle.bin']).stat().st_size
        command=c['runtime_command_common'];command[command.index('--input')+1]=c['paths']['input.bin']
    plan.update(amplification_tool_sha256=sha(Path(__file__)),amplification_purpose='Reduce fixed process/clock overhead for all short VM streams; >=40M original steps')
    (dest/'plan.json').write_text(json.dumps(plan,indent=2))
    print(json.dumps({'cases':len(cases),'amplified':sum('amplification' in c for c in cases),'plan':str(dest/'plan.json')}))


if __name__=='__main__':main()
