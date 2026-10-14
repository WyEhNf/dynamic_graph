# Actual production default versus old ordinary default

Frozen plan `808f6a035f036d83b9b7f48cee327a388af30cc25c2e9620e15a5da23cbde6c6` completed in actual session80050, exit0, 42.121s. All130 complete output files equal frozen original-C output streams. No original C program was reexecuted or regenerated for this performance batch.

Old4f73 and installed99a execute with their actual defaults, engineauto, no VM backend or budget override. Every source requires VM (optimized=none); native Cholesky performance is outside this cohort. This compares aggregate actual defaults, not one dispatch mechanism. Current compute includes decode. The old binary does not report VM steps/decode/plan metrics; those fields remain absent. Metadata/input/output IO, process wall, external SHA/comparison and Win32 counters are preserved independently.

All65 compute pairs improved, with no negative pair or tie. Per-source median ratios range 0.194242..0.478398. All thirteen sources are reused frozen data, including earlier holdouts; none is new holdout data in this stage. The denominator remains65 and all five ratios are kept.

| Source | Old median compute ms | New median compute ms | Five new/old ratios | Median ratio | Median wall ratio |
|---|---:|---:|---|---:|---:|
| changed-arithmetic | 211.917 | 89.771 | 0.481289, 0.432122, 0.397744, 0.441312, 0.384736 | 0.432122 | 0.596844 |
| changed-SSA | 195.653 | 89.289 | 0.434303, 0.511313, 0.374037, 0.457082, 0.479945 | 0.457082 | 0.600789 |
| generic-if-while | 229.070 | 82.667 | 0.337233, 0.376622, 0.371337, 0.378278, 0.329895 | 0.371337 | 0.534247 |
| int-arithmetic | 221.536 | 99.545 | 0.430754, 0.449340, 0.457704, 0.454315, 0.488281 | 0.454315 | 0.611581 |
| int-conversion | 326.063 | 86.679 | 0.264656, 0.260807, 0.276210, 0.297347, 0.300257 | 0.276210 | 0.484558 |
| deep-SSA40 | 375.459 | 89.205 | 0.225210, 0.254544, 0.237126, 0.243105, 0.240783 | 0.240783 | 0.398718 |
| nested-helpers | 433.741 | 84.841 | 0.186651, 0.211794, 0.197159, 0.182721, 0.194242 | 0.194242 | 0.337379 |
| SSA-conditional | 278.996 | 85.820 | 0.289531, 0.300826, 0.310083, 0.320303, 0.323905 | 0.310083 | 0.505597 |
| unused-double | 248.116 | 107.040 | 0.418961, 0.467193, 0.439142, 0.491840, 0.447313 | 0.447313 | 0.555319 |
| fresh-fma-control | 201.443 | 94.362 | 0.421962, 0.459083, 0.468733, 0.429900, 0.513860 | 0.459083 | 0.627491 |
| fresh-dependent-branches | 208.434 | 89.154 | 0.415459, 0.449281, 0.440062, 0.440965, 0.423568 | 0.440062 | 0.550487 |
| original-fp-builtin | 246.745 | 121.095 | 0.463069, 0.499711, 0.469694, 0.446995, 0.562674 | 0.469694 | 0.662361 |
| fresh-carry-fma-plain | 207.561 | 105.547 | 0.556381, 0.445365, 0.472647, 0.488583, 0.478398 | 0.478398 | 0.628081 |

Host busy counters ranged 21.81%..75.57%; minimum available RAM 1,014,173,696 bytes. PeakWS/commit reached 7,475,200/2,248,704 bytes. Project jobs were isolated; user background applications were untouched. One light Win32 process inventory was performed to report the requested actual PID, included in these host counters. No whole-host-idle assumption is made.

External SHA validation totaled 2921.342ms and whole-file comparison 1360.551ms; neither is inserted into compute. Full raw per-trial stdout/stderr and output files are retained. VM source scope, IO/wall distributions and host load limit interpretation; no official85-point or generic native-runtime improvement is inferred.

The actual installed binary and1e9 budget were unchanged during the batch. The prior N10000 full copy result remains explicit1e10 success and default1e9 rejection. Finite CFG budget proof is a separate unimplemented plan.
