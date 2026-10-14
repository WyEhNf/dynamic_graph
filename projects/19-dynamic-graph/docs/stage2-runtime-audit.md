# 19 题运行能力与下一方案审计

本次只审阅源码、冻结报告和 primary 资料，没有运行新基准或修改 runtime/前端。已验收普通 Runtime 为 4f73；AVX-512 的 d4e5 候选及 60 次结果另外冻结，完整候选源码补存 `artifacts/stage2-avx512/candidate-source/snapshot-manifest.json`。

## 实际能力和缺口

| 层次 | 实际支持 | 可复现限制 |
|---|---|---|
| C 前端 | 三/四参数 int/void 函数，两条一维 double 输入/输出指针、int N/可选 block；int32/double 局部、for/while/if/条件表达式、数学 builtin、纯标量 SSA helper | 签名按 Clang 类型明确检查；二维 VLA、局部指针别名、restrict 变体、堆分配、globals、递归、带语句分支/可变状态 helper、float/unsigned/wide 类型不在当前子集 |
| 完整源码执行 | 33 opcode PROGRAM 执行实际控制流、所有参数/initializer 一次求值，未初始化检查、int32 UB 检测、动态数组边界、有限输出和返回状态检查 | 一般合法 C 只能使用串行 VM；threads 不使未知依赖的 PROGRAM 并行。保留完整图不等于已经支持一般图并行 |
| 原生证明 | 左看、右看和连续分块 Cholesky 的完整操作/循环域证明；显式 fma、纯 int selector、已证明 counted while | `changed-arithmetic`、一般 if/while、deep SSA、整数 helper、未使用 initializer 等仍为 optimized=none，不能根据外形套标准 Cholesky |
| 动态 N/M | IO 与执行入口检查 3≤N≤10000，逐矩阵流式；已对一般 dense10000 执行真实原 C 并核 800,000,008 字节 | VM 默认 10^9 原 opcode 步数。合法 cubic 程序在最大 N 仍可能触发限额；维度接受不代表任意合法 C 在最大 N 可以实用速度完成 |
| Metadata | 完整图、PROGRAM、顺序/jump/依赖保留；schema1/2/3、新最小候选与可选无损容器已验证 | 它是本地接口与受信前端契约；不能从文件缩小推定官方15分，通用图字段尚未驱动一般并行 scheduler |

典型拒绝要继续保留：unused int initializer/argument 的范围错误，INT_MIN/-1、零除、uninitialized scalar、非有限输出、不可证明 helper 副作用和错误数学签名。此前 405 次原 C 全文件与 53 个拒绝，以及 helper 49/17、while 63、integer selector 105/12 的分项不能当成“任意 C 已支持”。

## 现有成本证据

普通 4f73 冻结基础报告的同一个 scalar M15 输入，auto/tiled compute 0.486ms、强制 VM 171.540ms；官网转录为 0.446ms 与 227.035ms，最大矩阵129。它们是功能批的单次观测，支持识别数量级缺口，不能当隔离性能提升比。合法 changed-madd PROGRAM 143 条、deep-SSA40 266 条、generic while-if 49 条仍留 VM。

最新 same-binary AVX2 性能的 N10000/t16/B96 五轮 compute 中位1701.700ms，graph87.062ms（约5.12%），kernel1346.690ms（约79.14%）；任务198,485、状态1,588,720字节，packed410,296,320字节。B128分别1603.160/83.756/1263.050ms，任务85,320、状态683,192字节、packed414,187,520字节。这里的 graph 计时实际包含 packed 分配、约410MB清零以及节点构造；kernel 包含线程创建、调度/同步和全部P/T/U，不能把它解释为纯数学或锁成本。完整compute还包括输入校验、输出分配/生命周期等，不能用三个中位直接做可相减归因。

因此删除全部 graph_ms 的理想上界在这两个受测几何也仅约5%，真实可删除部分更小；不能因为任务198k就推定它主导成本。现有 NONE 初始化、lazy graph/prefix、serial walk、column workspace、packed queue、八行和 AVX-512 已有正负记录，本轮不重复它们。余下约80% kernel 的锁、面板和U占比没有分项 profile；此刻选择另一调度重写缺少因果证据。

## 选择：保留语义的 prepared VM

本轮优先提高所有 VM 适用 PROGRAM 的解释执行效率，不扩大数学证明、不重写源算法。提供一个隔离、默认 OFF 的 `--vm-backend legacy|prepared`；只有真正进入 VM 的程序受影响，native/AUTO/普通4f73仍冻结。

采用三项组成同一个 backend 的一般策略：

1. 由原 PROGRAM 生成运行时只读 decoded plan，CONST 保留 double 全位，槽/jump/array immediate 使用整型字段；原 PROGRAM、完整图和 Metadata 文件不变。不按源名、hash、N、特定 opcode 序列挑选算法。计划按 Metadata 建立并复用M个矩阵，decode 时间和内存明确记录。
2. 使用有界 backing stack 和两个显式顶栈寄存值，减少 vector push/pop、容量判断、重复top地址计算；initialized 标志可用字节数组。深度语义仍是0..4096，额外临时容量用于执行后按原位置发现overflow；所有33 opcodes保持原pop顺序和错误顺序。
3. GCC/Clang提供独立 computed-goto dispatch；其他编译器使用相同decoded/TOS实现的switch。跳转label由本Runtime的枚举表生成，既不读传入指针，也不写入Metadata。第一版不做 superinstruction 合并、IP聚合、dead-evaluation 删除或JIT，保持每原opcode执行前 `++steps` 的完整限额契约。

即使 immediate 已在 read_metadata 中验证，C++调用者也可能直接构造Metadata。prepared路径不得把原先仅在执行某条非法 immediate 时才出现的错误提前到不可达代码：可记录invalid immediate并在对应原PC触发，或对这种手工对象回退legacy；不能静默接受它。uninitialized、array index、int32 conversion/overflow、WRITE finite、RETURN状态/栈平衡都继续动态检查。失败仍不发布输出并清理partial。

适用前提是当前已经接受的 PROGRAM/输入契约；不要求Cholesky形状、固定N、矩阵稀疏性或无分支。每个FP64操作保持原顺序和操作数；只对显式FMA执行 `std::fma`，plain不能融合。未使用helper参数、initializer和TRUNC（即便重复）仍计入原步骤并执行。正常舍入及subnormal环境沿用当前契约。计划不声称支持更多C类型、一般依赖图并行或解决最大N cubic复杂度。

最大N的限额缺口单列：右看三角更新次数 N(N−1)(N+1)/6，N10000有166,666,665,000次，每更新至少一个原opcode就已超过默认10^9。优化dispatch不能同时保留步骤契约又绕过它。最大N一般VM验证需明确较大 `--vm-step-limit` 且选 O(N²) 合法C；不能伪称prepared VM让任意cubic10000可用，也不擅改默认限额。

## primary 依据及迁移边界

[Lua5.0 实现原论文](https://www.lua.org/doc/sblp2005.pdf) 第7节阐述寄存操作数减少栈搬运，同时指出解码与代码体积的代价；只用于本地TOS/decoded设计依据，不转移其速度数据。[Lua5.4.9 lvm.c](https://www.lua.org/source/5.4/lvm.c.html) 与 [ljumptab.h](https://www.lua.org/source/5.4/ljumptab.h.html) 是当前实际实施示例，包含寄存寻址、编译器条件dispatch和异常前保存PC/top；本项目保持自身int32/FP契约。

[Ertl/Gregg2003](https://jilp.org/vol5/v5paper12.pdf) 讨论解释器的indirect dispatch与分支预测成本；其模拟与硬件不能替代本机测量。[Ertl等2006原论文](https://www.complang.tuwien.ac.at/cd/papers/A73-full.pdf) 指出superinstruction遇到异常/quickening的语义困难，因此第一版保留每个原opcode，不复制可执行机器码。

[Ertl/Paysan ECOOP2024](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.14) 及其原PDF把IP更新依赖链作为现代CPU上的独立瓶颈；即使更换dispatch，仍可能留下该限制，本次不预设收益。[LLVM LangRef](https://llvm.org/docs/LangRef.html) 的默认FP环境与fast-math/strictfp区别用于检查浮点边界；此方案没有LLVM JIT依赖，也没有借编译器许可进行重结合。

## 开发与验收计划

第一步独立 prepared build 与backend选择，保留legacy同二进制基线；Metadata/program不变，编译strict FP flags、packed OFF，AVX-512 OFF。只添加VM plan、TOS和dispatch，记录prepare_ms/execute_ms/plan bytes、原vm_steps；prepare成本不得被移出总compute而伪造运行收益，CLI/多矩阵Metadata总装载成本另外说明。

第二步在独立目录冻结源/EXE/C harness/input/完整output SHA，覆盖全部33 opcode独立数值golden（零符号、subnormal、溢出、显式FMA），任意合法jump/不平衡栈、0/1/4096深度边界、预算恰到RETURN/少一步、全部UB及失败cleanup。对每个执行故障核相同错误类别和触发原PC；合法手工Metadata及不可达坏操作另测。所有支持source的legacy/prepared与真正原C完整字节三方对照；原native405/53只做必要回归，不重复昂贵10k cubic C。

第三步先统计不同VM实际执行步数与旧成本，再冻结有限性能计划：同一新EXE、相同source/Metadata/input/C oracle、五轮交替legacy/prepared；至少覆盖changed-arithmetic、changed-SSA、generic while-if、deepSSA、int conversion/arith、nestedhelper、unused-double和forced-VM plain/explicitFMA。不拿单个demo或大文件IO占比冒充通用吞吐。规模按此前实际步数/时间选择，过小源的decode固定开销负例保留；大O(N²)源另做N10000原C完整输出，明确限额参数与资源。

只在root再次释放性能窗后启动性能。分别报告plan建立/执行、总compute、IO/wall、所有负值、五对比值及范围；若TOS/dispatch没有跨程序可靠收益，保留负结果并不晋升。官方85/15仍无法由本地时间/字节推定。
