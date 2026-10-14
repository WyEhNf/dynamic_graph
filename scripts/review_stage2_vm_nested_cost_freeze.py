"""Audit final frozen artifacts without repeating already accepted full-byte tests."""
import json,time
from review_stage2_vm_nested_next_sources import ROOT,D,read,sha
def main():
    f=D/'policy-cost-acceptance';m=read(f/'manifest.json');audit=read(ROOT/'outputs/stage2-root-vm-nested-cost-actual.json')
    assert sha(f/'manifest.json')=='b477bfd5c88faf637fc488f63d294549fdb7abaf6b3677ae9b33a0e9ddfa318e'
    assert m['passed'] and m['actual_tool_session_id']==54561 and m['actual_terminal_exit_code']==0
    assert audit['passed'] and audit['report_sha256']==m['report_sha256']==sha(D/'policy-cost/report.json')
    for name,row in m['frozen_files'].items():assert sha(f/name)==row['sha256']==sha(row['origin'])
    result=dict(passed=True,reviewed_unix=time.time(),acceptance_sha256=sha(f/'manifest.json'),frozen_files=len(m['frozen_files']),actual_whole_byte_audit_sha256=sha(ROOT/'outputs/stage2-root-vm-nested-cost-actual.json'),scope='Final frozen sources/buildprovenance/EXE/rawlogs/reports match every origin. Separate actualroot audit independently verified all174wholeC bytes and87pairs; freeze review does not rerun performance or output comparisons.')
    (ROOT/'outputs/stage2-root-vm-nested-cost-freeze.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
