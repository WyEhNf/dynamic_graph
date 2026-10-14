# Optional nested VM: actual policy cost results

The frozen same844 fixed/proved experiment completed all174 executions and87 pairs, with every whole-file result equal to its real original-C reference. The optional proof is retained without default promotion. Ordinary99a still uses fixed1e9 and proofOFF.

There were 73 negative pairs and 14 wins, including 63 negatives among69 VM pairs. All outcomes remain in the report. The new short rectangle/triangle/unknown batches show visible proof overhead; larger old streams have smaller relative overhead. Native controls run no proof, so their small timings do not measure proof speedup.

Whole-host busy was 3.36–33.14%; available RAM minimum was 4947062784bytes. User applications were untouched. Compute includes both proof stages/selection/decode; process wall, IO, SHA checking and full-byte comparison are recorded separately.

| Case | Engine scope | Median proved/fixed compute | First proof ms | Nested proof ms |
|---|---|---:|---:|---:|
| changed-arithmetic | vm | 0.9938 | 0.237 | 0.970 |
| changed-SSA | vm | 0.9624 | 0.216 | 0.970 |
| generic-if-while | vm | 1.1002 | 1.715 | 5.013 |
| int-arithmetic | vm | 1.0502 | 5.713 | 0.000 |
| int-conversion | vm | 1.0348 | 4.780 | 0.000 |
| deep-SSA40 | vm | 1.0886 | 4.701 | 0.000 |
| nested-helpers | vm | 1.0649 | 4.161 | 0.000 |
| SSA-conditional | vm | 1.0704 | 4.313 | 0.000 |
| unused-double | vm | 1.0048 | 0.223 | 1.078 |
| fresh-fma-control | vm | 1.0711 | 0.666 | 6.131 |
| fresh-dependent-branches | vm | 1.0292 | 1.362 | 0.000 |
| original-fp-builtin | vm | 1.1039 | 3.170 | 0.000 |
| fresh-carry-fma-plain | vm | 1.0671 | 0.555 | 5.018 |
| control-scalar-auto-dense | native | 0.7183 | 0.000 | 0.000 |
| control-scalar-auto-diagonal | native | 1.0274 | 0.000 | 0.000 |
| control-page-tiled-dense | native | 1.1691 | 0.000 | 0.000 |
| control-blocked-auto-dense | native | 1.0307 | 0.000 | 0.000 |
| nested-rect-strides-dense | vm | 7.1515 | 0.088 | 0.308 |
| nested-rect-strides-signedzero | vm | 7.1212 | 0.093 | 0.294 |
| nested-triangular-dense | vm | 3.9918 | 0.091 | 0.279 |
| nested-triangular-signedzero | vm | 3.6466 | 0.093 | 0.279 |
| nested-gram-three-dense | vm | 1.0667 | 0.111 | 0.611 |
| nested-gram-three-signedzero | vm | 1.0867 | 0.107 | 0.620 |
| strict-cholesky-control-dense | native | 0.9412 | 0.000 | 0.000 |
| strict-cholesky-control-signedzero | native | 1.2000 | 0.000 | 0.000 |
| unknown-data-step-dense | vm | 2.1980 | 0.087 | 0.155 |
| unknown-data-step-signedzero | vm | 2.2464 | 0.087 | 0.162 |
| unknown-parent-bound-write-dense | vm | 3.1797 | 0.084 | 0.204 |
| unknown-parent-bound-write-signedzero | vm | 3.0615 | 0.085 | 0.198 |

Ratios above1 are slower. Sub-millisecond native controls and the two small positive old-case medians are not evidence of a causal general speedup. No source, input, worker setting, step limit or kernel was changed between paired commands.

The separate25 high-N analysis-only probe matched15 predicted bounds and10 unknown safety cases. It allocates no matrices or executes C/VM. That evidence establishes the proof result, not full large-shape output acceptance. No N10000 matrix execution or default budget change is included here.

Actual report: `artifacts/stage2-vm-nested-budget/policy-cost/report.json`; immutable source/raw/summary manifest: `policy-cost-acceptance/manifest.json`. Every large output retains its original path plus the SHA obtained during the actual full-stream comparison. Freeze does not reread/copy the495920904-byte output set.
