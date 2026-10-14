# Next execution optimization: one entry-safe pair mechanism

The nested proof experiment preserved every original-C byte, but 63 of69 VM
cost pairs became slower. Proving a larger finite budget changes reachability;
it does not reduce the number of executed instructions. The next proposed
experiment therefore targets dispatch/fetch work. There is no implementation,
compiler invocation, new VM test or performance execution for this proposal.

## Current evidence and static scope

The already frozen phase3 machine code has three actual indirect dispatch
sites after GCC tail merging, an inlined pop helper, and roughly24 KiB of code.
It improved the measured real VM-required corpus as a whole, but that did not
isolate branch prediction from pop inlining/code layout. TOS2 stack caching had
60 negative pairs and is not combined with this proposal.

Current `threaded_vm.cpp` retains a chain on every opcode: check end, update
lastpc, increment/check original steps, copy decoded record, increment PC,
validate enum and dispatch. NEXT also checks4096-stack overflow after the
completed operation. These checks are semantic obligations; their repetition
is a candidate cost, not a measured dominant hardware stall.

`execution-static-design-v2/plan.json` analyzes the full unchanged PROGRAM of
all13 earlier generic C sources and six current C holdouts. Nineteen source
identities are retained, including duplicate-equivalent PROGRAMs. Eighteen are
actual VM-default sources; the strict Cholesky holdout remains a native bypass
control. Each full C source and Metadata is copied with SHA. Complete CFG,
reachable PCs, explicit jump targets, block entries, every safe bigram and
every excluded side-entry pair are recorded.

There are175 entry-safe LOAD+LOAD sites across all19 PROGRAMs. These are static
occurrences, not executed counts or percentages of time. No speedup estimate
is inferred from them. The first producer used the wrong spelling INTDIV for
the real canonical IDIV; its failed partial directory and source are retained
in `execution-static-design`, and the corrected static result is in the new
v2 directory. No Runtime or Metadata encoding was changed.

## One proposed mechanism

An opt-in fixed-span LOAD+LOAD superinstruction can remove the generic indirect
dispatch, enum check and repeated decoded-fetch dependency between two eligible
loads. Discovery uses adjacent opcodes and the full CFG, never source names,
hashes, N, sample data or the independent triangle step formula. A pair with an
external entry into its second opcode is excluded. Invalid/unknown discovery
falls back without diagnosing an unused operand.

The first LOAD completes its original immediate check, initialized check,
push and NEXT overflow check. Then the second LOAD independently performs its
original step/limit/lastpc update and checks. No span-wide step precharge is
allowed: with a limit between the loads, the first must have happened before
the second budget rejection. Stack depth4096 must still be observed at each
intermediate point. The original vector stack is retained; this does not add
TOS2 caching, constant folding, FP arithmetic fusion or reassociation.

All jumps and errors keep original PCs. All other33-opcode semantics remain:
initialization, indices, checked int conversion, division/remainder errors,
operand pop order, nonfinite results, signed zero, subnormals, and explicit
fma versus plain multiply/subtract. Complete Metadata/PROGRAM stay unchanged.
Any discovery/decode cost stays inside compute, without persistent plan cache.

Fifteen frozen counterexample groups include full original instruction lists,
prefix budgets, unused bad operands, side entry, invalid/uninitialized slots,
both intermediate stack-overflow boundaries, int division/remainder UB,
bounds, direct IEEE bit injections and return underflow. These are proposed
test gold, not newly executed results. Existing934/33-opcode contracts and
the full624-C/56-error corpus remain the semantic baseline if implementation
is later authorized.

## Primary basis and limits

Ertl/Gregg discuss static superinstructions reducing dispatch and stack
operations, with implementation, compilation and code-size tradeoffs. Their
machine-specific historical results do not establish a benefit here.
[Original paper](https://www.complang.tuwien.ac.at/anton/euroforth/ef03/ertl-gregg03.pdf).

Ertl/Paysan identify VM IP-update dependence as a possible critical path for
lightweight loop-dominated programs and describe several ways to reduce it.
Our proposed pair addresses one fetch/dispatch link; it preserves per-op
steps and error PCs, so actual assembly and measurements must establish
whether the remaining chain dominates.
[ECOOP2024 paper](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.14).

The current stable function-local label machinery must retain noinline/noclone
behavior and safe C++ object lifetimes; labels cannot jump between functions,
and computed goto does not perform ordinary scope-exit destructor handling.
[GCC documentation](https://gcc.gnu.org/onlinedocs/gcc/Labels-as-Values.html).

Strict FP flags remain explicit `-fno-fast-math -ffp-contract=off`.
Clang documents that no-fast-math alone still sets contraction to on; it is
insufficient as a byte-equality guarantee for plain mul/sub programs.
[Clang manual](https://clang.llvm.org/docs/UsersManual.html#controlling-floating-point-behavior).

LLVM ORC is a credible larger JIT architecture with compilation and symbol
management, but a JIT would add backend/dependency/strict-FP and error-contract
work. It is deferred rather than bundled into the bounded pair experiment.
[ORCv2 design](https://llvm.org/docs/ORCv2.html).

If separately authorized, one candidate must first demonstrate actual fewer
dispatches/fetch dependencies and record tail merge/code growth. Then use the
same candidate EXE's original threaded and explicit fused modes, fixed budget
and proofOFF, with all13 old streams/repetitions plus six unamplified fresh
C streams. Native AUTO stays native. Five alternating pairs per source, all
full-C bytes, compute including decode, external IO/SHA, resource/load and all
negative results are required. No default promotion follows merely from
passing small contracts or observing static sites.
