# Validated VM default integration: ordinary installed and maximum shape verified

Phase3's actual130 files/65 pairs and378 whole-C files have been independently
audited. Its e27 candidate, forced fallback, source snapshots and reports remain
frozen. This next stage changes default selection only. It does not add a new
kernel, stack, opcode, fusion, arithmetic rule or Metadata format.

The integration source enables prepared VM and GNU-label dispatch. The
library and CLI default backend becomes `auto`. In a VM-required program it
selects GNU threaded when the compiler's feature probe succeeded, original
decoded switch when label dispatch is unavailable or explicitly forced portable,
and original legacy switch when preparation was disabled at build time. Metrics
name the effective backend (`decoded-threaded`, `decoded-fallback`, `decoded`,
or `legacy`). Existing native recognition and AUTO shape/tile rules run before
this selection and remain unchanged. Backend selection never forces native
programs into VM; use `--engine vm` for an intentional VM execution.

`--vm-backend legacy`, `decoded`, `decoded-threaded` remain explicit overrides
when compiled; the negative TOS2 candidate remains explicit only. The original
per-opcode step checks and1e9 default step budget are unchanged. Local ordinary
preset pins the new VM options ON so a pre-existing CMake cache cannot silently
retain OFF. The memory preset explicitly pins both OFF; its7da06 EXE remains
untouched. The historical ordinary4f73 EXE was verified against the already
frozen phase1 ordinary baseline and copied to this stage's `ordinary4f73.exe`.
Its actual historical source provenance is
`artifacts/stage2-runtime-release/release-manifest.json`; `source-before/` is
the later phase3 source, not the original4f73 source.

Isolated GNU/default and forced-portable Release builds both passed all12
CTest entries (152.04s and143.17s respectively). Their strict FP/native/SIMD
flags match the accepted phase3 configuration. A preparation-disabled build
also passed the selector contract. New API tests cover default selection,
explicit overrides, effective backend on errors, signed zero, unreachable
invalid immediate and the original budget. Existing934/404/480 contracts and
100,000 raw stack payload operations pass; Clang UBSan passed934 contracts
and the new selector. Across the prior13 C sources and63 input/FP families,
all378 complete output files equal actual frozen original-C outputs across
old ordinary default, new default, explicit threaded/decoded/legacy and actual
portable default. Seven failure programs preserve status, message and absent
output in all six modes. No timing claim is inferred from this functional
batch. Ordinary Release `99a87d135378406a15efd930d58941291683ca799f91bd5dcc0ca77ceadef448` is now installed. Its actual8 contract tests
and147 complete C outputs (63 generic,60 wire,24 minimum-format) passed,
plus7 exact error contracts. The isolated functional acceptance remains
frozen. Old4f73 is archived and memory7da06 remains installed unchanged.

`acceptance-manifest.json` freezes the actual new binaries, source, compile
flags, contract logs and CTest evidence. `rollback4f73/` contains the original
released source, recorded build settings, release manifest and exact4f73 EXE.
It is distinct from the later Phase3 `source-before/` snapshot. Binary rollback
is an exact copy; the historical source snapshot omits some test fixtures and
is suitable for a runtime-only rebuild with `BUILD_TESTING=OFF`. No fresh
rebuild of that historical source is claimed in this stage.

Maximum shape then uses the original legal while-copy C source and its complete
N10000 input. This is O(N²) generic VM coverage, separate from already validated
dense native Cholesky. The original C binary is reexecuted sequentially and
its entire800,000,008-byte output compared to the historical C output before
any VM backend. Source, harness, Metadata, input, C binary and reference SHA are
verified before execution; there is no candidate-produced reference. At least
2.5GiB RAM and4GiB free disk are required before starting; free RAM is checked
again before every backend. No other backend or original C matrix is held
concurrently. If resources decline, completed rows remain and pending rows
wait; user applications are not disturbed.

First the GNU default backend runs with the unchanged default1e9 budget and
must reject this1,700,000,012-step program with no published/partial output.
Then GNU default threaded, explicit decoded and actual portable default each
run sequentially with explicit `--vm-step-limit 10000000000`. Every complete
output is compared over all800,000,008 bytes; real PeakWS/commit, free RAM,
background CPU, compute/prepare/read/write/wall and external checks are kept.
This only demonstrates the explicit budget configuration. It must not be
reported as a default-budget generic N10000 pass.

## Actual maximum-shape result

The frozen plan completed with actual exit0. OriginalC was reexecuted and
all three backend outputs matched its entire800,000,008 bytes, including
1,700,000,012 original opcode steps. Every process launch passed a fresh
2.5GiB RAM gate. GNU default1e9 rejected exactly with the original error
and no published/partial output; only explicit1e10 configurations passed.
Actual PeakWS values were1,605,718,016/1,605,718,016/1,606,373,376 bytes
for GNU auto/decoded/portable auto; commit and background CPU are preserved
in `maximum-shape/report.json`. These sequential resource tests are not a
new paired performance claim. The accepted source/flags, ordinary actual
binary, current documentation and147 installation outputs are frozen in
`ordinary-install/`; old manifests and sources remain unchanged.

## Independent future budget policy decision

The official N3..10000 range concerns Cholesky input sources. Current recognized
plain/blocked/FMA sources execute native at all supported shapes, independently
of the VM instruction budget. The broader generic C fallback is a local
extension and its current1e9 limit does reject the N10000 copy; that gap remains
explicit. Increasing a universal constant because this one source needs1.7b
steps, using N² scaling without a source proof, or deleting the limit would be
an unjustified change. A generic cubic VM program can need over1.6e14 original
steps at N10000, so a larger arbitrary constant does not solve general support.

A separately specified `auto` budget could use an independently verified
finite control-flow bound B(N,block) for applicable affine counted loops. It
must count every original opcode, include every branch's maximum cost and
loop test/exit, use checked integer arithmetic, and verify bytecode CFG,
induction updates, loop-entry state and trip bounds against the complete
PROGRAM. It cannot trust a source name/hash or a frontend-claimed bound alone.
Bounded nested loops and guarded zero-trip domains must be covered. Unproved
data-dependent loops retain the conservative1e9 cap; explicit CLI limits
remain exact overrides. B is finite and becomes the execution cap, never an
unlimited loop exemption. Administrative work/timeout caps would be separate
and must produce an explicit rejection rather than falsely claiming full
support. This is a research proposal, not an implemented default.

Before such a policy can be adopted, an independent plan must test malformed
and false certificates, changed PROGRAM and jump entries, infinite/overflowing
induction, unsigned/wide integer rejection, branch-dependent bounds, nested
odd/zero-trip domains, exact last-step versus one-short budgets, repeated
execution, native-path independence, and actual N10000 behavior. Metadata
certificate overhead must be included in the15-point file-size evidence. Until
that separate verifier exists and is tested, the default stays1e9.
