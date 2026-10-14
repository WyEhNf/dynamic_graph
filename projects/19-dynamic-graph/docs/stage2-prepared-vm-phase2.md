# VM 第二阶段：双栈顶缓存

独立候选为 `323045ced55b390cfaccfebff542abd5455fc6cc0d6657f3dad1fe9518cf5516`，位于 `build-stage2-vm-tos2`，开启已有可选 `CHOL_PREPARED_VM=ON`后可显式添加 `--vm-backend decoded-tos2`。CMake默认仍OFF，已启用的研究构建也默认legacy；普通4f73、memory7da0、AVX候选及第一阶段bf54保持冻结。

本阶段只有两个scalar FP64栈顶字段和保存更早值的vector。`push_back`在第三个值入栈时将第二个值下沉，`pop_back`在需要时从冷层补入；不计算或解释这些值，允许保持负零/subnormal/NaN payload原位。编译器决定实际寄存分配，不能仅凭两个C++字段声称它们始终留在硬件寄存器。原handler、switch分派、33opcode、steps限额、pop顺序与执行后4096 overflow检查仍保留。没有goto、指令融合、初始化删除、Metadata/M缓存或数学算法改写。

cache状态只属于一次执行；每矩阵decode仍记入compute与 `vm_prepare_ms`，original Metadata/PROGRAM不变。decode plan是独立内存，`vm_plan_bytes_peak`没有把cache对象或原槽/栈/输入输出总内存加在一起，不等于进程峰值。

## 功能证据

| 用例 | 实际结果 | 保存位置 |
|---|---|---|
| 原33opcode全部404合同 | legacy/decoded/TOS2三方通过 | `tests/prepared_vm_tos2_tests.cpp` |
| 深度0/1/2/3/4/7/8/63/64/65/127/129/4094/4095/4096、DUP溢出、RETURN/异常、步骤预算 | 总480合同通过，4096→4097在原DUP指令结束后报错 | `native-contract.exe`、`correctness/report.json` |
| 独立raw stack模型，包括quiet/signalling NaN payload、±0、±subnormal | 100,000次冷热push/pop与vector全位一致，另全部drain验证 | 同上 |
| 9原VM必需C、2新C和实际FP builtin C，58家族 | 5后端共290次全原C文件字节一致，原步骤相同 | `correctness/report.json` |
| 原有7类整数/转换/零除错误 | frozen bf54与新legacy/decoded/TOS2的错误文本/status/partial清理一致 | 同上 `failures` |
| 项目完整回归 | 10/10，146.86秒，68832 exit0 | `ctest.log` |

新源 `fresh-fma-control`结合nested while/for、纯helper、条件表达式及显式FMA；`fresh-dependent-branches`包含分支初始化、短路判断以及合法读取此前输出位置。它们的shape为3/11/67/139/193/257，相比旧9源3..129单列为fresh holdout。第三个补充源是第一阶段的FP builtin源，本阶段同样使用这些新尺寸，不能当新源码。dense、signedzero、subnormal、large、near-rank-one全家族保留；int conversion限制在原C整数转换可定义的前三类家族。

这次功能批允许项目并发，290份只证明执行契约，不报告加速。`candidate-manifest.json`冻结EXE/native测试与111份actual source/test/frontend/CMake flags到 `candidate-source/`。第一阶段源/EXE另存 `source-original/`与 `phase1-baseline.exe`，旧报告不覆写。

## 独立性能预声明

唯一计划为 `artifacts/stage2-prepared-vm-phase2/performance/run-plan.json`，SHA为 `77501a71459508a7a9beb77a8723382e18262d7c4f91119876f7c3d96f12ee5b`。同3230 EXE比较decoded（第一阶段算法）与decoded-tos2，全部12源×5交替轮=120次，不拿两个不同binary混合归因。bf54用于功能合同基线，不作为本次性能的另一二进制。

只按冻结dense原步骤数决定完整M流重复次数，目标每trial至少4千万步骤，保留所有源与负值；参考矩阵字节来自实际执行的原C输出，外层M重写独立说明。每trial验证candidate/source/Metadata/input/oracle binary/harness/参考SHA，并完整逐字节核对输出。decode在compute中，读取/写入/总IO、进程wall、外部SHA和对照成本单列。

宿主用户应用保持运行，Win32逐trial记录真实RAM、进程PeakWS/commit、CPU及背景负载；项目批隔离不表示整机空闲。根释放窗口后实际session45560 exit0，120次完成，46.334秒，所有完整原C文件和trial SHA通过。宿主busy区间19.60%..50.00%，最小可用RAM3,560,587,264字节；SHA总2.576秒、逐字节对照总1.624秒在runtime成本外单列。

| 源 | decoded/TOS2 compute中位(ms) | paired中位TOS2/decoded | 完整五对比值 | TOS2胜数 |
|---|---:|---:|---|---:|
| changed-arithmetic | 210.656 / 242.799 | 1.167808 | 1.206394,1.183940,1.167808,1.152585,1.159056 | 0/5 |
| changed-SSA | 210.881 / 252.646 | 1.198050 | 1.285924,1.275684,1.162650,1.198050,1.129145 | 0/5 |
| generic-if-while | 220.070 / 234.698 | 1.118885 | 1.118885,1.040714,1.135112,1.057351,1.165864 | 0/5 |
| int-arithmetic | 222.084 / 255.370 | 1.131499 | 1.131499,1.149880,1.195665,1.105875,1.130016 | 0/5 |
| int-conversion | 215.087 / 247.879 | 1.169705 | 1.191269,1.169705,1.046786,1.110708,1.253824 | 0/5 |
| deep-SSA40 | 234.789 / 302.414 | 1.262913 | 1.254281,1.230836,1.262913,1.437669,1.310057 | 0/5 |
| nested-helpers | 232.517 / 261.997 | 1.126786 | 1.239358,1.117856,1.089501,1.312482,1.126786 | 0/5 |
| SSA-conditional | 208.766 / 248.970 | 1.201267 | 1.174334,1.239687,1.206921,1.146807,1.201267 | 0/5 |
| unused-double | 245.137 / 302.369 | 1.258500 | 1.196653,1.101256,1.265926,1.325252,1.258500 | 0/5 |
| fresh-fma-control | 209.993 / 245.804 | 1.182835 | 1.149357,1.205920,1.184175,1.076953,1.182835 | 0/5 |
| fresh-dependent-branches | 206.587 / 246.140 | 1.165996 | 1.161704,1.203429,1.165996,1.123342,1.231830 | 0/5 |
| original-fp-builtin(新shape) | 257.690 / 292.001 | 1.133148 | 1.162470,1.060557,1.177145,1.105604,1.133148 | 0/5 |

60/60对为负，各源paired中位慢11.89%..26.29%，最坏deepSSA第3轮慢43.77%。完整成本、内存和背景观测保留于 `performance/report.json`，只表述当前宿主背景下的结果。两个新源也没有收益，不用旧9源的某个快点规避失败。TOS2默认OFF且不晋升、普通4f73/第一阶段bf54不替换。

这个结果证明本次实现没有收益，并不提供branch/spill的精确归因：C++两个字段可能需要不同检查/搬运，编译器不保证它们驻留寄存器；没有独立性能计数器profile前，不把这些可能原因当成已测瓶颈，也不在当前数据上继续调实现直到某组变快。

此前N10000一般while-copy为第一阶段资源验证，实际1,700,000,012步骤超过默认10^9，只在显式10^10预算下四后端通过；不能说默认VM最大形状已通过，也不能说TOS2已验证了最大形状。本阶段保留该事实，不重跑它充当新holdout。

设计依据为此前已核验的[Lua5.0原论文](https://www.lua.org/doc/sblp2005.pdf)栈/寄存权衡、[Lua5.4实际实现](https://www.lua.org/source/5.4/lvm.c.html)和[Ertl/Paysan2024](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.14)的IP/dispatch瓶颈讨论。没有照搬外部代码或套用其速度数据；栈缓存是否收益由完整本机配对决定。官方85/15和一般C支持限制仍见需求审计。
