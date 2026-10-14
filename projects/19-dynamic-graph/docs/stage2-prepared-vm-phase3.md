# Phase3: optional decoded threaded dispatch

This candidate changes dispatch only at source level. `CHOL_THREADED_VM=OFF`
remains the build default; enabling it requires `CHOL_PREPARED_VM=ON`, and even
that build still defaults to `--vm-backend legacy`. Ordinary Release4f73,
phase1bf54 and phase23230 binaries and their snapshots remain frozen. Metadata,
PROGRAM, native mathematics and AUTO tile policy are unchanged.

Frozen phase1 machine code already has a primary jump table at0x140007b13 and
a second binary-operation table at0x140007b80. Its vector pop lambda is called
as a real function at0x140001f00. Steps and their budget are checked before
fetch; the decoded record is indexed by old PC, and PC advances by one.
Phase2's decoded baseline retains equivalent machinery. These are actual
disassembly observations, not a claim that switch performs33 comparisons.

`decoded-threaded` uses one function-local33-entry label table, the same
typed-operand preparation and an ordinary vector stack. Each binary label
pops right then left and performs its original operation directly. It has no
TOS2 cache, fusion, plan cache, code copying or cross-function label pointers.
An out-of-range enum selects a dedicated handler that still pops two operands
before throwing. Preparation never rejects unreachable bad immediates. Each
original opcode retains its step, error order, PC and4096-stack boundary.

All owning objects are constructed before the first dispatch. Handler blocks
have only scalar temporaries and close before NEXT; RETURN and exceptions
unwind normally. GCC noinline/noclone and a static label initializer keep
addresses local to a stable function; Clang uses noinline. This follows the
[GCC labels-as-values restrictions](https://gcc.gnu.org/onlinedocs/gcc/Labels-as-Values.html).
The [Lua5.4 dispatch implementation](https://www.lua.org/source/5.4/ljumptab.h.html)
and [Ertl/Gregg interpreter study](https://jilp.org/vol5/v5paper12.pdf) motivate
testing the mechanism. [Ertl/Paysan2024](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.14)
also motivates checking PC dependency; this candidate does not eliminate it.
No external implementation code was copied.

The compiler's first Release output contains only three actual indirect
dispatch sites: initial0x140018297, common NEXT0x14001830e and jump
NEXT0x140018793. GCC merged most handler tails. The binary secondary table is
gone, but the unchanged pop lambda was automatically inlined, and the new
function is roughly24KiB versus5.6KiB for old decoded. There is no forced
inline attribute or stack rewrite. A future same-binary paired result can
measure this compiled mechanism as a whole; it cannot isolate branch-only
effects or infer speed from the source pattern.

A CMake compiler probe gates GNU labels. Without them, or when
`CHOL_THREADED_VM_FORCE_PORTABLE=ON`, requesting this backend runs the original
decoded switch and reports effective `vm_backend="decoded-fallback"`, including
on exceptions. The fallback translation unit contains no computed goto.

Small acceptance is frozen in
`artifacts/stage2-prepared-vm-phase3/small-contract-manifest.json` with126 actual
source/build/flag files and GNU, forced fallback and sanitizer executables.
Both GNU and fallback pass934 comparisons, preserving the original480 cases
(including404 phase1 cases), then adding all33 jump-entry/per-budget checks,
empty/one/two-operand invalid enum errors, repeated exceptional unwinding and
unused faulty instructions. Old404 and480/100000 raw-stack suites also pass.
Clang21 with actual MSVC ABI and standalone UBSan passes the same934 tests;
strict FP flags remain enabled. Initial standalone sanitizer attempt90668
failed because the direct build omitted native CMake macros; corrected50935
completed successfully. The failed attempt is retained in the manifest.

Full acceptance uses the12 prior real-C sources and every FP family, with
source/input/Metadata/reference/oracle/harness SHA checks and complete binary
comparison. A new helper/carry source alternates explicit fma and ordinary
multiply/add, reads prior outputs under short-circuit control, and tests new
shapes5/19/71/131/211/263. Frozenbf54 is an independent functional baseline;
current legacy, decoded, threaded, default and forced fallback are checked.
The batch passed378 complete-C comparisons and7 error cases across six
backends, with all original step counts retained. Project CTest passed11/11
in113.02 seconds (actual73743 exit0). All timings from this batch are functional
observations, not paired speed claims.

The unique predeclared performance plan is
`artifacts/stage2-prepared-vm-phase3/performance/run-plan.json`, SHA256
`3dc6440370ee8ed18f4bd8c68690e71f5a25e0ff01718c125904da2dea3d2ec6`.
It specifies all13 sources times5 alternating pairs,130 executions in the
same e27candidate EXE. Twelve are prior performance sources; one is the new
source and shapes. Each complete actual-C matrix stream is repeated according
to its original steps to reach40 million steps, with no timing-dependent
selection. Decode is inside compute; SHA and byte comparison are separate.
Every trial records actual host CPU/available RAM/PeakWS/commit. User
applications remain untouched and are not assumed idle. The authorized130-record batch completed as actual29234 exit0 in32.418946 seconds. All130 full-file checks passed;65/65 compute pairs favored threaded. Default remains OFF.

Decode remains per execution and is included in compute, with plan bytes and
prepare time reported separately. This stage does not change the default
1e9-step contract: the previous N10000 copy used1.7b steps and required an
explicit1e10 budget. It cannot be presented as a default-budget N10000 pass.


## Complete paired measurements

Ratios are threaded/decoded; every five-round pair is retained. Times are
compute milliseconds including per-matrix decode. The wall ratio includes
process startup and I/O, excluding separately measured SHA/byte checks.

| Source | Decoded median | Threaded median | All five compute ratios | Paired median | Paired wall median |
|---|---:|---:|---|---:|---:|
| changed-arithmetic | 154.151 | 73.243 | 0.445025/0.519809/0.472195/0.473213/0.500916 | 0.473213 | 0.636613 |
| changed-SSA | 145.042 | 72.573 | 0.481591/0.504399/0.466645/0.443011/0.518967 | 0.481591 | 0.661708 |
| generic-if-while | 156.187 | 70.936 | 0.445631/0.432763/0.465606/0.447565/0.440302 | 0.445631 | 0.666364 |
| int-arithmetic | 154.648 | 76.698 | 0.527748/0.483835/0.517995/0.518753/0.529144 | 0.518753 | 0.685893 |
| int-conversion | 147.948 | 66.445 | 0.472525/0.415187/0.433938/0.455349/0.464859 | 0.455349 | 0.674857 |
| deep-SSA40 | 177.284 | 70.310 | 0.419895/0.380008/0.377055/0.420793/0.396595 | 0.396595 | 0.605293 |
| nested-helpers | 152.686 | 62.450 | 0.415907/0.371082/0.412271/0.399906/0.426551 | 0.412271 | 0.637451 |
| SSA-conditional | 147.127 | 72.141 | 0.466793/0.457099/0.463385/0.503160/0.490331 | 0.466793 | 0.702738 |
| unused-double | 172.227 | 79.523 | 0.504460/0.419582/0.455916/0.476355/0.476562 | 0.476355 | 0.605142 |
| fresh-fma-control | 146.397 | 76.332 | 0.521404/0.514560/0.523846/0.505533/0.518128 | 0.518128 | 0.653074 |
| fresh-dependent-branches | 147.482 | 73.882 | 0.502992/0.486441/0.530044/0.466905/0.495253 | 0.495253 | 0.648275 |
| original-fp-builtin | 176.978 | 87.244 | 0.467277/0.488191/0.494063/0.477785/0.496032 | 0.488191 | 0.675835 |
| fresh-carry-fma-plain | 157.884 | 82.712 | 0.514553/0.523260/0.535792/0.539811/0.492711 | 0.523260 | 0.632840 |

Source paired medians range 0.396595..0.523260, or 47.67%..60.34% less compute in this measured corpus. There were no negative or tied compute pairs; that empty negative set is explicitly retained. Twelve sources are prior performance cases and one fresh source/shape holdout; these are VM-required C sources, not native Cholesky. This does not establish arbitrary C support or change the default budget.

Actual host busy counters ranged 4.32%..27.08% during the trials; user background applications were untouched. Minimum available RAM was 9723355136 bytes; maximum process PeakWS/peak commit were 7475200/2285568 bytes. External SHA checks summed 1635.319ms and full-byte comparisons 992.080ms. Every trial contains compute, decode, Metadata/input reads, output writes, wall, CPU, memory and external checks; per-source medians for each cost are in performance/summary-audit.json. No large files were rehashed during the following static freeze.
