"""Run focused final-source tests and persist this turn's reviewed evidence."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'outputs/continuation-validation-2026-10-12'
parser = argparse.ArgumentParser()
parser.add_argument('--collect-existing', action='store_true', help='Reuse passed logs after the first timestamp-only failure')
options = parser.parse_args()
if not options.collect_existing: DEST.mkdir(exist_ok=False)
elif not DEST.is_dir(): raise FileNotFoundError('Original passed test logs are required')
commands = [
    (11, 'projects/11-context-governance', '.venv/Scripts/python.exe',
        ['-m', 'unittest', 'tests.test_candidate_gate', 'tests.test_governance', 'tests.test_contract_audit', '-v']),
    (19, 'projects/19-dynamic-graph', '.venv/Scripts/python.exe',
        ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_dispatch_profile.py', '-v']),
    (27, 'projects/27-aicore-streams', '../18-isa-scheduler/.venv/Scripts/python.exe',
        ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_prefix_memory_certificates.py', '-v']),
]
tests = []
for number, directory, python, argv in commands:
    cwd = ROOT / directory
    command = [str((cwd / python).resolve()), *argv]
    log = DEST / f'project{number}-tests.log'
    if options.collect_existing:
        transcript = log.read_text(encoding='utf-8')
        if transcript.strip().splitlines()[-1] != 'OK' or 'Ran ' not in transcript:
            raise RuntimeError('Retained unittest run did not complete successfully')
        code = 0
    else:
        run = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=60)
        log.write_text(run.stdout + run.stderr, encoding='utf-8')
        code = run.returncode
    tests.append({'project': number, 'argv': command, 'cwd': str(cwd),
                  'actual_exit_code': code, 'log': str(log),
                  'reused_completed_log': options.collect_existing})
    if code: raise RuntimeError(f'Project {number} tests failed; raw log preserved')

def read(relative): return json.loads((ROOT / relative).read_text(encoding='utf-8'))
audit18 = read('outputs/mobile-backbone-full336-audit-2026-10-12.json')
profile19 = read('projects/19-dynamic-graph/artifacts/dispatch-profile-verified-2026-10-12.json')
cert27 = read('projects/27-aicore-streams/reports/prefix-memory-certificates-final-2026-10-12.json')
assert audit18['passed'] and audit18['inputs'] == 336
assert profile19['count'] == 19 and all(row['original_C_selected_matrix_byte_equal'] for row in profile19['records'])
assert cert27['count'] == 24 and cert27['distinct_obstructed_prefixes'] == 5
files = [
    'docs/four-project-assessment-2026-10-12.md',
    'projects/11-context-governance/src/context_governance/candidate_gate.py',
    'projects/11-context-governance/tests/test_candidate_gate.py',
    'projects/18-isa-scheduler/scripts/audit_mobile_backbone_full336_result.py',
    'projects/18-isa-scheduler/experiments/r196-mobile-backbone-full336/report.json',
    'outputs/mobile-backbone-full336-audit-2026-10-12.json',
    'projects/19-dynamic-graph/tools/profile_vm_dispatch.py',
    'projects/19-dynamic-graph/tests/test_dispatch_profile.py',
    'projects/19-dynamic-graph/artifacts/dispatch-profile-verified-2026-10-12.json',
    'projects/27-aicore-streams/scripts/prefix_memory_certificates.py',
    'projects/27-aicore-streams/tests/test_prefix_memory_certificates.py',
    'projects/27-aicore-streams/reports/prefix-memory-certificates-final-2026-10-12.json',
    'scripts/record-four-project-continuation.py',
]
hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}
hashes.update({str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in DEST.glob('*.log')})
result = {'checked_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
    'assessment': 'docs/four-project-assessment-2026-10-12.md',
    'authorization': 'Current user request resumes development of all four projects, including previously paused project11.',
    'tests': tests, 'project18_semantics_controls': {'actual_exit_code': 0, 'tests': 4, 'tool_chunk': '02f5b8'},
    'project18': audit18,
    'project19': {'sources': 19, 'all_selected_matrices_byte_equal': True,
        'executed_load_pairs': sum(row['executed_load_pairs'] for row in profile19['records']),
        'large_shape_dynamic_coverage_measured': False, 'Cplusplus_speed_measured': False},
    'project27': {key: cert27[key] for key in ('count', 'original_cases', 'distinct_saved_prefixes',
        'distinct_obstructed_prefixes', 'distinct_obstructed_input_records', 'certificates')},
    'limitations': {'project11_new_model_quality_measured': False, 'project18_Level1_3_proved': False,
        'project19_default_promoted': False, 'project27_new_recoveries': 0,
        'official_scores_measured': False, 'old_frozen_evidence_preserved': True},
    'retained_intermediate_reports': ['projects/19-dynamic-graph/artifacts/dispatch-profile-2026-10-12.json',
        'projects/27-aicore-streams/reports/prefix-memory-certificates-2026-10-12.json',
        'projects/27-aicore-streams/reports/prefix-memory-certificates-verified-2026-10-12.json'],
    'initial_recording_error': {'tool_chunk': '661f9f', 'type': 'ZoneInfoNotFoundError',
        'scope': 'Timestamp persistence failed after all three child tests had returned exit0 and logs were saved.',
        'repair': 'UTC+08:00 timestamp; collect existing completed logs without repeating tests.'} if options.collect_existing else None,
    'file_sha256': hashes}
with (ROOT / 'outputs/four-project-continuation-2026-10-12.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
print(json.dumps({'status': 'passed', 'focused_test_suites': len(tests), 'project18_original_inputs': 336,
                  'project19_sources': 19, 'project27_saved_states': 24}))
