# Finite bytecode budget: static plan, not implemented

The ordinary99a87d release and its1e9 instruction budget are frozen. The
maximum-shape copy actually needs1,700,000,012 original steps; explicit1e10
passes, fixed1e9 rejects. This proposal addresses that budget gap without
changing dispatch, FP arithmetic, PROGRAM, Metadata or native selection.

LLVM's [loop terminology](https://llvm.org/docs/LoopTerminology.html) distinguishes
header/latch/backedges and warns that loop information does not cover every
cyclic CFG. Its [ScalarEvolution interface](https://llvm.org/doxygen/classllvm_1_1ScalarEvolution.html)
distinguishes exact and conservative backedge counts, with an explicit unknown
result and extra predicates when required. These inform the design; an LLVM
source-level estimate is not proof of this VM's complete PROGRAM. No LLVM
implementation or extra library is proposed.

## First implementation boundary

Start with an isolated optional `proved` budget mode. The published default
remains fixed1e9; explicit `--vm-step-limit` always has its literal fixed meaning.
An explicit proved mode combined with a literal limit is rejected as ambiguous.
No arbitrary N-based multiplier or source/filename/hash recognition is allowed.
A successful runtime proof gives a finite original-opcode upper bound B for
this PROGRAM and actual shape/block scalars. Effective proved budget is
max(1e9,B), with checked uint64 arithmetic and B strictly below UINT64_MAX.
An unknown proof retains1e9; it does not raise a new VM error or remove the cap.

The first proof subset is acyclic programs and one or more disjoint, unnested
natural counted loops. A loop has one dominating header, one latch, a
preheader initialization, a `<` guard, a positive constant integer induction
increment on every backedge path, and a loop-invariant integer bound. Acyclic
branches, early exits and arbitrary existing FP/memory body operations can
remain, provided none controls or overwrites the induction or bound.
Nested, irreducible, data-controlled and unsupported cycles return unknown.
These are structural conditions, not a signature for the copy demonstration.
Descending/inclusive/nested loops can be separate later extensions after this
subset has independent evidence.

## Proof steps and invariants

1. Build a conservative CFG from actual opcodes/jump operands, treating RETURN
   as terminal. Detect all reachable cycles, including irreducible SCCs.
   Invalid jump/slot/opcode or an unsupported analysis state returns unknown.
   Analysis must not emit an execution error for an unreachable instruction.
2. Propagate abstract stack and slot values through acyclic prefixes. Shape
   and block slots begin with actual runtime values; later STOREs are honored.
   Exact integer constants and interval/affine induction expressions suffice.
   READ becomes unknown. FP or integer operations not independently justified
   become unknown rather than relying on source annotations. Stack merges
   must agree in depth; unknown values may not prove a loop guard/update.
3. Prove the guard compares the induction slot to an invariant known integer.
   Check every path to the latch updates that induction exactly once by the
   same positive integer, with no alternate entry, bypass, hidden store or
   guard-bound write. Initial value, increments and their TRUNC/intermediate
   operations remain exact and within original int32 conversion bounds for
   every iteration, including the final failing guard. A false range or a
   possible wrap/rounding transition yields unknown.
4. Derive T=max(0,ceil((bound-start)/increment)) by checked integer arithmetic.
   Compute the longest original-opcode path in the acyclic body and exits.
   Include all guard evaluations, latch JUMP, every conversion, final failing
   test, prefix and RETURN. Collapse each verified loop into a finite weighted
   node and prove the remaining CFG acyclic. Conservative early-exit bounds
   are permitted; underestimated bounds are never permitted.
5. Retain the exact original per-opcode ++steps, PC, stack and runtime error
   checks. Only the selected finite limit changes in opt-in proved mode.
   Proof time and memory belong to each execution and are counted in compute;
   no cross-run cache is added. Native execution bypasses this VM proof.

For the existing copy PROGRAM, the original prefix has3 opcodes, guard7,
body/latch10, and return suffix2. Therefore B=3+7(T+1)+10T+2=17T+12.
At actual N10000, T=N*N=100,000,000 is within int32 and yields exactly the
observed1,700,000,012 steps. This arithmetic is a manually derived golden,
not a recognized source signature or an already implemented verifier.

## Evidence required before adoption

- Independently constructed bytecode goldens and a small exhaustive interpreter
  count: zero/one/odd trips, starts other than0, increments1/2/3, disjoint loops,
  acyclic branches and early returns. B must never be below actual original
  steps; exact fixtures must match B and reject at one fewer step.
- False proofs/mutations: jump into the body, bypassed/multiple induction
  writes, changed bound, shape-slot overwrite, loop reentry, nested and
  irreducible cycles, data-dependent guard, zero/negative step, int32/uint64
  overflow, fractional/nonfinite scalar and malformed used/unused immediate.
  Analysis must fail closed to fixed budget without changing later error
  status, message, PC or pre-error step order.
- All33 opcodes and934 existing contracts; explicit0/1e9/1e10 and exact step
  boundaries across legacy/decoded/threaded/portable; same decode/proof cost
  inclusion. Preserve ordinary99a87d and source snapshots before edits.
- Full actual original-C files for existing13 sources plus new source/shape
  holdouts; actual C remains the reference. Audit original Metadata bytes and
  complete graph/PROGRAM unchanged. No certificate means zero file overhead.
- A separately authorized sequential N10000 resource batch, fresh RAM gates,
  original C/cache full800,000,008 bytes, fixed1e9 refusal and proved finite
  budget behavior. Only after this actual run may a proved-policy N10000 pass
  be reported, and only for the structurally verified subset.

The verifier itself needs a finite analysis-work bound. Its CFG/abstract-state
work counter must return unknown if the bound is exhausted, with that cost
recorded. A proof permitting a very expensive cubic VM is still not a speed
claim or a promise to finish an unlimited workload. Operational timeout policy
is a separate decision and must not be hidden in a correctness claim.
