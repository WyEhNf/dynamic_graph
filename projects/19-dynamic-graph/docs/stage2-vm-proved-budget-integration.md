# Isolated finite PROGRAM budget integration

The published ordinary runtime remains the frozen99a87d binary with fixed1e9
steps. The separate `CHOL_PROVED_VM_BUDGET=ON` build exposes
`--vm-budget proved`. The CMake option is OFF by default, and the runtime option
still defaults to `fixed` even in an enabled build. No default installation or
maximum-shape execution was part of the first small functional stage. A
separately authorized maximum-shape functional resource gate has since passed,
described below; the ordinary default remains unchanged.

The frozen first component is
`artifacts/stage2-vm-proved-budget/component-acceptance/manifest.json`
(07481fb2fc9c6cdbe4a197230907c07dbd6a828feb29e7bf6431c1508954db48).
Its actual agent-run gate comprises517 independent goldens,1030 exact/one-short
boundaries,119 unknown cases,6358 PROGRAM mutations,416 proved mutations and832
real old-VM executions. Root subsequently rebuilt the frozen component with
the separately frozen exact historical ABI headers and476ad core library;
actual compile/test both exited0 with all counts matching, recorded in
`outputs/stage2-root-vm-proof-component.json`.
The failed first test attempt is retained: it modified an ignored POP operand
instead of the induction CONST. Final component work accounting also charges
CFG/vector/abstract-state copies; no VM execution code changed in that stage.

## Policy and execution contract

After all original native selections, the generic VM optionally analyzes the
actual complete PROGRAM with actual N/block scalars and a250000-unit work cap.
Success chooses `max(1000000000, proved_bound)`; unknown retains1000000000.
No source name, hash, filename, demonstration formula or Metadata certificate
selects this policy. Every original opcode, step increment, PC update, stack
check and arithmetic/error operation remains in the existing VM backend.

`--vm-budget proved` conflicts with **every explicit** `--vm-step-limit`,
including the literal1000000000 and irrespective of option order. `fixed`
continues to accept literal limits. In the C++ API,
`vm_step_limit_explicit=true` records an explicit literal default limit;
proved mode also rejects any nondefault limit even without that marker.
An OFF build rejects proved mode. Invalid policy strings are rejected.
Native paths do not analyze PROGRAM or change their geometry/FP behavior.

Per-execution API metrics record proof status/reason, finite bound, work,
effective cap and elapsed proof time, including when later VM execution fails.
CLI aggregates proof time/work and proved/unknown/not-run matrix counts, with
peak bound and maximum effective cap. Analysis and its transient allocations
belong to each execution; proof time is included in `compute_ms` and separately
reported as `vm_budget_proof_ms`. No persistent proof cache is introduced.

## Functional plan

1. Compile independent GNU enabled, portable enabled and disabled builds using
   only this project's F-drive compiler temporary directory. Preserve actual
   flags, commands, TEMP/TMP/TMPDIR, disk availability, raw logs and exit codes.
2. Run the existing934 fixed-policy contracts unchanged. The derived proved
   contract test changes only nonboundary runs to proved mode; explicit small
   per-op boundary tests remain fixed, and still exercise all33 opcodes and
   original step/error ordering. Preserve its exact original-source digest and
   transformation. A separate policy gate compares all enabled backends on
   invalid used/unused immediates, unknown analysis, work exhaustion, integer
   UB, nonfinite results, signed zero, FMA, explicit conflicts and native bypass.
3. Reuse all63 frozen original-C source/family groups across13 genuinely generic
   sources, with full files/headers/source/input/Metadata/C oracle hashes. Run
   seven real enabled runtime modes: candidate fixed-auto, proved-auto,
   proved-legacy, proved-decoded, proved-TOS2, proved-threaded and portable proved.
   Add fresh stride2 and disjoint-loop C sources at odd heldout shapes7/13/29/53,
   dense and signed-zero diagonal inputs, compiled/executed by real GCC.
   Record full-file comparisons and actual proof status, including all unknowns.
4. Check CLI explicit-limit conflicts in both orders, fixed literals, disabled
   policy refusal, help advertising and output/partial cleanup on failure.
5. Freeze complete current source, actual GNU/portable/disabled EXEs and logs.
   Preserve ordinary99a87d and memory7da06 hashes. Only after the small gates pass
   prepare a separately authorized sequential N10000 resource plan.

The first structural subset is conservative and intentionally returns unknown
for nested, descending, inclusive, data-controlled, irreducible or unsupported
loops. At the component stage, the N10000 copy bound1,700,000,012 was only a
mathematical golden. The later actual proved-policy pass is recorded below.
Fixed1e9's observed
refusal remains an explicit limitation of the ordinary default. No new speed
claim, official score estimate or removal of an execution cap follows here.

## Actual first runtime gate

Three isolated Release builds compiled successfully using process-local F-drive
compiler temp. Enabled GNU and portable each passed11 small CTest contracts;
disabled passed9. Clang UBSan actually ran all four original934, derived934,
component517/mutations and80-policy-comparison executables successfully. Its
MSVC LNK4217 linking warnings remain in the raw log; no runtime sanitizer
diagnostic occurred. The original failed policy test and correction remain:
the fixture incorrectly expected stage for the unchanged auto diagonal native
path; the corrected fixture verifies both auto diagonal and dense stage bypass.
No runtime/component/math code was changed for that correction.

The actual seven-mode full-C gate completed469 byte-identical output files:
63 historical groups×7 plus four fresh source/family groups×7. All15 C sources,
input headers, complete Metadata and actual C references are preserved.
Seven expected source-error families×seven modes retain exact stderr/status and
no published/partial output. Nine CLI policy/conflict/disabled/help cases passed.

The proved-auto run analyzed566 matrices:306 proved and260 unknown. Those
unknown results are retained, including nested/while/FMA-control sources outside
the initial structural subset. Both new source families proved all eight
matrices per source (dense/signed-zero, shapes7/13/29/53). All effective caps in
this small gate remained1e9, so these files validate semantic equivalence and
fallback; they do not validate a raised-budget maximum-shape execution.
Proof time remains inside total compute; functional runs may overlap other
projects and are not a paired performance measurement. The GNU complete CTest
pipeline actually passed15/15 after183.378 seconds; portable11/11 and disabled
9/9 small contracts are supplemented by the portable full-C gate. No duplicate
native-C pipeline for all three builds or new long performance sweep was run.

The acceptance manifest, immutable source/ABI headers, three runtime EXEs,
contracts, CTest logs and strict-FP build provenance reside in
`artifacts/stage2-vm-proved-budget/runtime-integration/acceptance/`.

## Actual N10000 opt-in functional resource gate

The frozen5d88d2bf plan and actual session10759 completed with exit0. Each launch
was sequential and passed a fresh2.5GiB RAM and remaining-disk gate. The actual
original-C reference is the previously compiled/executed full800,000,008-byte
file, with input/source/harness/Metadata/EXE SHA verified; no new C reference was
created. All three output files include the complete header and matrix and have
SHA `ba1de265d437ca11c555be4872076421963c24226bebe12264888530d61b0929`.

| Requested backend | Effective VM | Actual steps / proved bound / cap | Proof work | Proof ms | Peak working set bytes | Peak commit bytes |
|---|---|---:|---:|---:|---:|---:|
| GNUauto proved | decoded-threaded | 1,700,000,012 | 822 | 0.079 | 1,605,816,320 | 1,604,050,944 |
| GNUdecoded proved | decoded | 1,700,000,012 | 822 | 0.078 | 1,605,791,744 | 1,604,022,272 |
| portableauto proved | decoded-fallback | 1,700,000,012 | 822 | 0.113 | 1,605,976,064 | 1,604,038,656 |

No explicit `--vm-step-limit` was supplied. The actual PROGRAM proof selected
the finite upper bound; proof and decode remain included in compute. Raw JSON
also separates metadata/input/output I/O, whole-process wall, external SHA and
full-file comparison cost. These single functional/resource executions are
**not** an isolated paired performance experiment or an official score claim.
Host busy percentages were19.57–23.45%; user applications were untouched.
Launch free RAM was5,900,951,552 /5,887,037,440 /6,016,528,384 bytes and minimum
available RAM during the three successful processes was4,278,689,792 bytes.

The first fixed-default run actually exited1 with
`error: VM instruction limit exceeded` and no result/partial file. Fixed1e9
still rejects this1,700,000,012-step source; the ordinary99a binary and its
default policy are preserved. This result establishes the optional policy for
this structurally proved source at N10000, not every supported C or unknown
loop. Full records and all terminal output remain in
`artifacts/stage2-vm-proved-budget/maximum-shape/report.json`
(b5d986a6379306bf0a48074bb8d3bb161ad6520b25b688e3d231c61ee794f15b).
