# One proposed extension: recursive natural counted-loop summaries

This is static design only. Keep the accepted first proof component, ordinary
runtime, current budget policy and existing unknown results frozen. The design
uses the already-read LLVM [loop terminology](https://llvm.org/docs/LoopTerminology.html)
and [ScalarEvolution contracts](https://llvm.org/doxygen/classllvm_1_1ScalarEvolution.html):
single-entry natural loops, explicit unknown, conservative counts, and checked
range assumptions. It does not borrow a source-level LLVM estimate as a VM
certificate or require an LLVM runtime dependency.

The observed gap is complete bytecode with nested counted loops. First stage
rejects overlapping head/latch intervals and retains1e9. A generic two-dimensional
pointwise source, with N outer rows and N inner columns, can therefore fail at
N10000 despite having finite int32 induction and O(N²) total work. Native
Cholesky already bypasses the VM proof; this extension targets actual generic
PROGRAMs, not a source name or a copied17N² demonstration formula.

Propose only a recursive extension of the existing increasing `<` induction
subset. Do not add descending/inclusive guards, extra dispatch, caching, FMA,
metadata certificates or a new default in the same experiment. Build a natural
loop forest from complete conservative CFG predecessor/backedge reachability,
verify single entry and dominance, and reject shared/irreducible cycles. A
parent with child summaries must still prove that every remaining cycle is
covered; an apparent textual interval alone is insufficient.

Analyze leaves first. At a child preheader, propagate exact integer constants
and parent-induction **ranges**, all constrained to original int32 and exact
FP64 integer arithmetic. Shape/block scalars begin with actual values. The child
initialization must occur on every entry and not depend on unknown data or a
value retained from a prior parent iteration. Any relevant uninitialized,
fractional/nonfinite, overflow-sensitive or unsupported expression yields
unknown. Body READ/FP operations may remain unknown when they do not establish
progress or a bound.

For a first conservative parent-dependent child guard, derive an upper bound
Tmax across the full proved parent-IV range, including zero trips and the last
valid iteration. A rectangular constant child bound is a special case. Do not
try an exact triangular polynomial sum in this stage. Child cost is
`(Tmax+1)*guard + Tmax*longest_acyclic_body`, including every original conversion,
latch JUMP, child initialization and exit suffix at the corresponding parent
positions. Replacing a child node by this conservative weighted summary and
then applying the original parent trip bound may overcount, but cannot skip
original opcodes or reduce their step contract.

Each summary carries all possibly written/uninitialized slots, entry/exit stack
depths, early-return/exit edges and proven invariant constraints. Parent guard
or IV writes hidden inside a child are forbidden. A parent-IV read used as a
child bound is stable for that child invocation; a child write to that parent
IV invalidates the proof. On child exit, kill non-invariant slot constants and
retain an induction value only when every non-return exit proves it. Never
carry a first-iteration abstract value into subsequent iterations without an
invariant argument. Stack entry/exit shapes must agree across every path.

Continue checked uint64 weighted arithmetic with bound strictly below UINT64_MAX,
checked signed-int/FP exact ranges, and charged CFG/state/summary copying under
the existing finite work cap. Depth exhaustion or uncertain effects return
unknown and retain fixed1e9; no execution error is emitted for untaken faults.
No cross-run proof state may survive a changed PROGRAM, shape or block.

Before any Runtime integration, independently construct 2/3-level rectangular
and triangular-bound goldens; exhaust small shapes/starts/steps against the
actual original VM, all zero/one/odd and early-exit combinations. Mutate child
entry/latch, skip initialization, retain previous IV, overwrite parent IV/bound,
add side entries/irreducible edges, alter stack merges and force int32/uint64
overflows. Require every returned bound >= actual pre-error steps. Then repeat
all33/934 semantic contracts and real-C fresh pointwise sources/shapes, with
separate N10000 resource authorization. This proposal claims no new proof or
maximum-shape pass yet.
