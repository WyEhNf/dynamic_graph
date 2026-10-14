# Optional nested VM: frozen measurement preparation

This stage prepares experiments, without claiming a runtime speedup or official
85-point performance result. The installed ordinary runtime remains `99a87d…`,
with fixed `1e9` VM budget and proof disabled. The isolated accepted GNU candidate
`844c9749…` and its native/AUTO/math/Metadata behavior are unchanged.

## Same-binary cost scope

`artifacts/stage2-vm-nested-budget/policy-cost/run-plan.json` freezes 29 cases:
all 13 earlier genuine VM performance streams with their original repetition;
six current true-C source holdouts in dense and signed-zero families; and four
earlier native controls. The strict Cholesky holdout is a native AUTO control in
both families, so the total is 23 VM cases and six native cases.

Each case has three alternating pairs in case-major order: fixed/proved,
proved/fixed, fixed/proved. All 174 records and 87 pairs remain in the denominator.
The sole command variation is `--vm-budget`; the actual same accepted EXE,
input, complete Metadata, original-C output, workers, scheduler and block size
are frozen. Every pair uses the actual default threaded VM selection or native
selection. There is no fresh C compilation, oracle execution, amplification,
source-dependent selection or timing-based filtering in this cost experiment.

First-stage and nested-stage times/work/status are recorded independently.
Old first-proof predictions remain lineage and are not assertions of the final
nested status. The complete proof/selection and decode are included in reported
compute time; metadata/read/write IO, process wall, SHA validation and full-file
comparison remain separately visible. Native controls must have no proof work.
Negative pairs and unknown proofs are retained without default promotion.

Every launch records fresh RAM/disk gates, runtime-process PeakWS/commit/CPU and
raw whole-host CPU/RAM counters. Whole-host load includes user applications,
startup/IO, the monitoring process and our runtime. It is not an idle-host claim.
Raw stdout/stderr use files, avoiding an undrained pipe. The minimum launch RAM
is 256 MiB; disk must cover all remaining planned outputs plus 512 MiB. A resource
failure exits 75; a first execution/validation failure is preserved with raw
paths and an incomplete report. No automatic restart is permitted.

## High-N analysis probe

`artifacts/stage2-vm-nested-budget/analysis-only/run-plan.json` freezes 25
observations: rectangle, triangle and three-level Gram PROGRAMs, plus unchanged
data-dependent-step and parent-bound-write unknown controls, at N=3073, 6145,
8193, 9999 and 10000. Native bypass is tested in the six cost controls, not
inferred from an analysis-only proof call.

The C++ probe only reads complete Metadata and calls the accepted proof APIs.
It neither constructs a Matrix nor calls `read_matrix`, `execute` or any VM
instruction executor. Its allocation is confined to Metadata and proof data
structures. It links the frozen new-ABI `4598bcb8…` core with its matching
`1955d364…` runtime header and complete accepted source/header snapshot; the
old `57205…` core is explicitly forbidden. Strict FP compiler flags and all
accepted feature definitions are frozen in the future compile command. No
global ISA target flag is introduced.

The probe copies the accepted selection contract: first proof receives 250000
work units; a successful first proof skips nested analysis. Unknown first proof
calls nested only when checked remaining work is positive, even when the first
reason is `work-limit`. Total work must not exceed 250000. Unknown leaves cap
`1e9`; success uses `max(1e9,bound)`. Stage reasons, loop counts, work, remaining
work, selected stage, effective cap and stage/dispatch times are reported. The
static expected bound is only an independent test oracle and never routes the
runtime. All actual unknown/negative observations remain in the report.

Analysis does not prove whole large-shape C output acceptance or feasible runtime.
The N10000 triangle predicts 1,400,030,009 actual steps and a conservative bound
of 2,799,890,009, so a later separate full-C resource experiment can test a real
budget gap. The rectangle predicts 500,185,009 steps and already fits fixed
`1e9`. The Gram predicts 30,002,800,170,009 steps, so it is not proposed for large
execution merely because its bound is finite.

## Authorization boundaries and commands

The two `--prepare` commands completed only static file copying, byte/hash/header
checks and Python AST parsing. There are no new compiler, C, VM, proof or cost
execution results in this preparation. Future commands, each requiring the root
coordinator's source/resource or performance-window approval, are:

```
.venv\Scripts\python.exe tools\run_vm_nested_analysis_probe_stage2.py --compile
.venv\Scripts\python.exe tools\run_vm_nested_analysis_probe_stage2.py --run
.venv\Scripts\python.exe tools\benchmark_vm_nested_policy_stage2.py --run
```

All child-process TEMP/TMP/TMPDIR are restricted to the project F-drive compiler
temp. No global environment or user application is changed. A future N10000
Matrix/C/VM run is outside these runners and requires a separate sequential
resource window with at least 2.5 GiB fresh RAM and two 800000008-byte outputs
plus a 512 MiB disk reserve. No maximum execution or default installation occurs
here.
