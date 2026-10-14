# 19题阶段指标：2026-10-13

本轮保持原始 C 程序的完整字节真值，分别度量 VM、原生 Cholesky 与 Metadata。机器指标在 [阶段指标 JSON](../artifacts/project19-stage-metrics-2026-10-13.json)，原始命令、所有配对样本及失败记录保存在其中链接的 G 盘报告。

| 阶段 | 状态 | 当前指标 | 验收依据 |
|---|---|---|---|
| S1：VM默认优化 | 已安装 | 23/23 个 VM 数据流计算时间下降；逐数据流七对中位降幅的中位数 **11.09%**，范围 **3.37%–19.53%** | 400 个完整输出一致；13/13 CTest；405 次原 C 对照和53个拒绝场景；另4份新源码、12个矩阵及48个预算/PC/错误边界验证 |
| S2：Metadata换行 | 已接入默认前端 | 六源默认 schema2 总体积 **10,724→10,046 B（−6.32%）** | 36种完整图/PROGRAM等价、72份读取参数位值对照、288次原C完整文件比较；默认无参数与显式LF输出相同 |
| S3：原生内核 | 已验收，保留研究候选 | 6×8初轮N4096/N6145完整compute中位减少 **4.95%/6.03%**；新N4099的16线程compute反而增加 **3.74%**，因此未推广 | 原生全实验274次完整输出、390个矩阵与原C一致；6×8实验N6145峰值工作集OFF/ON为733.355/733.344 MiB |
| S4：前端启动成本 | 已接入默认前端 | 正常Clang调用 **3→2次**；18组成对分析耗时中位减少 **33.49%**，六源各自中位减少28.91%–36.58% | 30对完整Metadata/IR/analysis一致；36组图/PROGRAM、36组FPbits、144次原C输出比较；15解析控制、6真实控制及2独立新增控制通过 |

S1普通运行文件为 `build/cholesky_runtime.exe`，SHA256 `310aca2763797347ee36075f8608800daaf65a3b18c7e6c5bdda5fb7557d21b9`。安装后已在普通路径再次核验4个新增源码流、12个矩阵，确认实际使用 `decoded-threaded` 和固定10亿步预算。安装来源与回滚文件记录在 `G:/Hackathon-stage2-artifacts/project19/20261013-evening/installed-vm-default.json`；普通目录旧构建对象暂保留，新CMake构建会重新生成对象。原生AUTO策略及严格浮点规则保持现有行为。

S2新增 `--metadata-newlines lf|native`，默认LF；显式native可重现Windows的CRLF输出。默认schema仍为2；`--smallest-metadata`、压缩容器仍保留其原有显式选择规则。历史冻结文件及其哈希保持原记录。

S4从必需的AST调用标准Clang driver头获取真实版本；包装器前缀、重复版本或未知头格式继续独立查询，保留3次调用。没有持久版本缓存，也不从源文件可影响的IR ident提取。安装后普通前端实际确认2次Clang调用、版本相同、Metadata仍2119字节。耗时统计为`analyze()`函数完整时间，不含外层Python启动；小源码的进程启动成本占比较大。S4验收时前端SHA256为`40189828354f1d99e63f6bb35fecd4b3eefa4e8c9a50d55c3a6ed7b3fe1aa657`；夜间S5在此基础上加入显式批处理和省略IR。

| 来源 | 历史默认CRLF / B | 新默认LF / B |
|---|---:|---:|
| scalar | 2250 | 2119 |
| page | 2655 | 2499 |
| blocked | 3739 | 3491 |
| generic | 1107 | 1019 |
| negative-zero | 667 | 629 |
| noop | 306 | 289 |

未采用的候选也保留指标：3×12原生布局在五组测试中的kernel配对中位均变慢；6×8新Shape及显式FMA整体compute没有稳定改善；schema3读取快径的收益不稳定，测量部分存在宿主争用。这些候选保留隔离研究版本。原生实验完整计入图、kernel、分配及调度，不由一组kernel结果决定默认。

任务几何复测已完成：固定1537/4099/6145三个Shape、16线程、五对交替，B128完整compute配对中位改善分别为−7.78%/−2.16%/+7.39%，保留AUTO。N6145的中位数之比改善仅0.87%，波动原值同时保留；B128峰值工作集增加约2MiB。全部原生实验累计274次CLI输出、390个矩阵、29,709,308,528字节与原C一致。成本模型准确给出任务数和工作区，尚不足以预测最快分块。

下一阶段将分项定位原生compute成本。目前`graph_ms`包括factor分配与清零，不能当作纯图构造时间；N6145一组实测还有约97ms未单独归因。计划分出输出分配、factor分配/清零、纯图设置及输入释放，再据实测选择优化。此阶段尚未实施，不计作加速。

`compute_ms`包含分配、检查、图、调度和kernel；`kernel_ms`是其子项，CLI wall另含启动和读写。VM基准使用已有冻结C数据流，并重复短流使其达到至少四千万步；它不证明原生Cholesky的同等加速。各阶段比例独立报告，不相乘；本机结果与Metadata字节数均不换算官方得分。
## 夜间推进：显著收益后集中验收

S5已安装显式批量前端及`--skip-ir`。严格六输出批准备先获取并冻结源码/头文件依赖，Clang调用12→3；三对完整批处理时间中位4931.56→1468.68ms，成对降幅中位70.15%。显式省略IR降幅48.42%；普通单次完整审计仍两调用，该次三对中位为−3.48%，没有默认提速结论。168次原C全文件对照、36份完整图/PROGRAM、36份数值位、46份旧默认文件及13项快照/CLI控制通过，输出保护后补8项拒绝和1项正常CLI。安装前核对所有既有Python工具依赖相同，安装源码哈希与验收版本相同，未重复大套原C。实际前端SHA为`f323f2d4558d23ae742a8940eeacf77ec024c603956d93c5fd24573efce1d187`。证据及回滚：`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/frontend-vm/`。

S6跨矩阵显式工作线程上下文是隔离候选。新Shape实际CLI显式`--engine tiled --structure dense`的M9小批次、4/16线程分别减少19.31%/16.04%，均计入上下文初始化及最终join；M2/16线程减少−2.27%，不作统一收益声明。修复工作线程浮点环境复用后，2份原C、动态/IEEE矩阵及生命周期/异常清理集中验收通过；同一最终候选同样显式tiled的M9三对复测为17.49%/25.35%，M2本次为+4.83%，与前次负结果同时保留。默认AUTO在N<128会走另一StagePool路径，不能套用这些性能比例；默认AUTO性能另测。当前未安装该运行文件。

S7内存生命周期分项已闭合：12份instrumented样本逐次相加的最大未覆盖时间0.015ms；`graph_ms`包含packed因子分配和清零，`thread_join_wait_ms`包含实际工作，均不可把嵌套时间再相加。N6145一组三次中位：compute340.50ms、kernel254.64ms、输出清零33.49ms、因子清零17.73ms、因子与输入释放各约10.14ms，纯任务图设置仅0.055ms。跳过因子清零在该Shape反而变慢。

既有输入复用路径加每tile首任务初始化的性能筛选，在N4096/4099/6145相对普通baseline的配对中位减少25.58%/28.43%/20.48%，9/9对改善；包括返回结果释放的辅助口径仍9/9改善。probe保留额外master输入，峰值工作集456.42→329.98、456.95→329.89、1021.29→734.29MiB，不能写成实际CLI峰值。已有复用控制本身贡献收益，首任务初始化的单独增益尚不稳定。原C集中验收和无master实际CLI测量进行中，尚未推广。上三角暂存因子的替代路径9/9对变慢，停止该候选。

S8当前固定栈/指令引用基础上的LOAD+LOAD合并，只做三流三对性能筛选：配对中位+1.37%、−1.15%、+6.12%，没有统一显著收益，停止扩大验证，未改生产默认。源码、严格编译参数和全部负结果保留在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/vm-load-pair/`。

## 组合安装：2026-10-14夜间

当前普通运行文件为`d9de1273f6d9bc6aa03a8771e444fadad588d5f819da8e6ae205abe13071de03`，静态库为`63a60aeb5a26efe7351a8355b5527b3fd20a08b100dea88f6a216da0a6443e97`，两者均来自同一次完整G构建。安装前逐源合并、两份独立静态审阅后，集中组合验收包含4份重编API/契约控制程序、8份原C完整输出和6项异常/partial清理控制。未对每个小改重复运行大套测试。回滚与构建证据在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/combined/`。

S6/S7/S9及小AUTO策略现已安装；上节“未安装”等描述为各候选交付时的历史状态。S6默认AUTO额外测量的M9/4、16线程配对中位下降7.18%/13.06%，不能套用强制tiled的17%–25%数字。S7无master的实际CLI三图下降19.56%/31.43%/23.04%，峰值工作集约减少38.6%–39.1%；首任务初始化相对既有复用路径在N1024仍有−1.12%增量，保留负结果。

S9仅显式`--vm-plan session`启用。三份实际VM源码各20,000矩阵、N3/N7、六组五对compute全为正，配对中位降幅约9.78%–37.99%；nestedRect N7的wall仍有−0.58%，不称统一端到端提速。934契约×3typed后端×冷/热、53状态含512并发、25份原C完整流及portable+proved配置通过；proof每次按N/block重算，native和legacy不构建解码计划。

小AUTO策略只沿既有N<128域，在nearest且FTZ/DAZ关闭的调用环境使用原串行stage；显式stage/tiled、强制VM和非默认浮点环境保持原选择。旧候选69次原C/边界检查及批处理91.33%/99.21%compute收益已保留；加环境保护后的28对兼容控制另列，未冒称重测旧性能。下一轮仅对组合后的真实默认测量给出新指标。

本地旧object仍在，已安装EXE和静态库与新头文件对齐。再次构建应先运行`cmake --preset local-mingw`，再build；preset将旧cache中的workspace OFF选项更新为已验收ON组合。源、库和CLI哈希均由安装收据及阶段manifest记录。

证据归属勘误：S7的364次小API全输出对照，非FMA部分使用`fixtures/cholesky_reference.c`自建严格C参考，FMA部分使用独立标量`std::fma`链；这些API对照不能称为官方转录C对照。实际CLI的21份文件、33矩阵及1,995,796,080字节独立原C/FMA参考比较不受影响。组合验收中的storage API程序同样使用该自建fixture；其余8份CLI原C输出另有独立证据。历史文件和SHA保持原样，追加勘误在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/lifecycle/api-oracle-label-erratum.json`。

## S11：已安装组合的直接性能

实际比较组合`d9de1273`与回滚`310aca27`，固定七组各三对交替、42个CLI进程。engine/structure/backend/VM plan保持默认；明确区分显式parallel与完全不传执行选项的CLI默认serial/1线程。这次性能测量只核对退出、输出长度与矩阵数，正确性依据已有集中组合验收；没有重复大套原C验证。

| 固定负载 | 执行参数 | compute配对中位减少 | 整个进程wall配对中位减少 |
|---|---|---:|---:|
| 小矩阵M12 | parallel/16线程 | 99.18% | 53.67% |
| 混合M9 | parallel/4线程 | 45.11% | 0.78%（仅2/3对改善） |
| 混合M9 | parallel/16线程 | 57.66% | 12.27% |
| dense N4099 | parallel/16线程 | 28.41% | 11.14% |
| dense N6145 | parallel/16线程 | 28.69% | 17.75% |
| dense N4099 | 真正CLI默认serial/1线程 | 6.23% | 4.54% |
| dense N6145 | 真正CLI默认serial/1线程 | 6.65% | 6.41% |

21/21个compute配对均改善；不能把小矩阵线程成本的99%推广为大图收益，也不能将各单项比例相乘。M9/4线程compute改善并未转化为稳定显著的进程wall改善。首轮启动/读入缓存波动及所有配对原值保留，指标不代表官方得分。stage未报告kernel时间（原字段为0），该项不计算比例。汇总初次遇到零分母后只修离线聚合，没有重跑计算。证据：`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/combined/installed-performance/`。

## S12：显式factor容量缓存

隔离候选的`--native-workspace session`对重复四次N4096/N4099的实际CLI、每组三对compute配对中位减少9.33%/9.29%，6/6对改善；wall减少5.08%/5.22%，N4096仅2/3对wall改善且首对回退25.65%。峰值工作集约202MiB基本相同，不能称内存降低。保留冷单图、重复N6145、部分混合流及dense转band容量滞留负项；编译门和CLI默认保持OFF，没有新AUTO阈值。

一次集中验收含180个API完整输出比较（172对独立转录C及显式FMA C、8对并行舍入OFF/ON兼容）、188次成功native执行、5项预期拒绝；另16个大矩阵、2,149,057,168字节实际CLI输出匹配冻结C真值。覆盖N/B变化、首次任务清零、失败后恢复、close/reopen及共享workspace/context并发。转录题目源码的div/madd定义及L清零仍依据本地明确契约，非官方提供的helper定义。初始两次验收失败来自并行舍入期望错误，修正测试对照后核心及CLI字节未改。证据：`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/workspace-cache/workspace-delivery.json`。

## S13及最终组合：2026-10-14 01:40

当前普通CLI SHA256为`1afefeadf2fa33b41e1e1241c5bb4be279ed4465de81a2527c1077b4a25f347b`，core为`0a012a811949028d89ee795a348a067d20dde36d9d3b9c7a5217828bbad29899`。两者来自203文件冻结工作区的全量G构建，安装时完整核对所有编译源码/头文件及11项差异，并保存回滚。S12现已作为显式CLI选项安装，运行默认off；local-mingw编译门ON，全局CMake门默认OFF。历史S11测量的运行文件仍为d9de，不能冒充当前1afe的配对测量。

S13将内部解码记录32→16字节，保持原PROGRAM、PC、预算、无效索引的延迟错误及FP64立即数位值。默认auto/per-matrix下，N3三源compute改善24.15%/33.13%/39.43%，N7为10.22%/8.14%/26.56%，十二对均为正；解码vector容量字节数恰好减半，未声称整个VM堆或实际allocator内存减半。三份中长流三对逐矩阵compute为−0.86%/+0.71%/+4.09%，session为−2.53%/+0.31%/+2.38%；长generic全部三对回退，明确保留，未宣称长流通用加速。首发进程wall异常及所有原样本也保留。

候选集中验收包含全部33 opcode、ordinary/portable/proved、53状态与512并发、14,424条额外payload语义记录、28组FP位roundtrip、25份独立C完整流及6份小session流。新增FP标志检查首次混合hash不等后，逐记录诊断证明输出/error/steps/PC差异均0，旧版本自比也有2,403条INEXACT差异，来自现有chrono double计时；测试仅排除该非确定性位，invalid/div0/overflow/underflow仍检查。运行源码自性能筛选至最终集中验收完全未改，没有以改动runtime方式迁就错误fixture。

最终组合验收只做一次：3份API程序按新头/core重编，2份真实VM流完整C输出对照，以及以下4次固定CLI调用。没有生成新的8分钟原C参考；既存大资产先一次SHA预检，最终输出各一次完整SHA核对。

| 最终版本实际调用 | 结果与边界 | 单次compute | 峰值工作集 |
|---|---|---:|---:|
| N10000、完全不传执行参数 | serial/1线程/B64，缓存off，800,000,008 B与独立C真值一致 | 9,126.13 ms | 1,217,712,128 B |
| M=[4096,10000,4096]、parallel16、显式缓存session | B96，2次分配/1次复用，3次context任务；1,068,435,472 B完整真值一致 | 1,187.66 ms | 1,219,465,216 B |
| 成功矩阵后非SPD、显式tiled/session | 正确拒绝并完成线程/lease清理，无最终文件或partial发布 | 不作成功性能统计 | 小错误流资源单列 |
| 成功矩阵后多余尾字节、AUTO/session | 正确拒绝，无最终文件或partial发布 | 不作成功性能统计 | 小错误流资源单列 |

这是单次正确性/资源观测，串行单图与并行三图负载不同，不能互除声称加速。混合session最终容量410,296,320 B，最终释放31.339ms和worker join0.621ms均计入compute。真值依据官方图像转录的本地div/madd及L清零契约；历史原C生成报告未绑定当时compiler EXE SHA，该追溯限制保留。

完整构建、集中组合验收、安装/回滚证据位于`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/combined-next/`。旧F objects/test EXE不代表当前产品；后续本地重建须重新configure并生成objects，安装的EXE/core已与当前全部编译源码和头文件匹配。

## S15：显式结构化路径trim，当前安装版本

2026-10-14 02:27普通CLI更新为`e47af9a05111aaab3048e90d94359b6227c987d49e7330298d8e5d493a5e1157`，core为`6f6c6d31686fa48fdc33827e925981a2154323b1a480a22596d9e7df895b033c`。只更新3份源/头，完整新构建与头布局匹配，安装收据/回滚位于`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/cache-structured-release/session-trim-v2/`。上述1af的规模测量和配对性能为历史精确版本记录，不能冒称当前e47配对测量。

资源筛选只改已证明结构化路径的释放位置，固定18进程、54矩阵、19,238,918,976输出字节；筛选不做原C比较。dense10000→band10000峰值WS/commit三对中位降低20.34%/20.39%（约391MiB），3/3更低；compute中位改善1.96%，三组compute护栏均通过。wholewall仍分别为−11.92%（主例）、−22.32%（重新分配控制）、−4.33%（纯dense无close控制），全数保留。9/9对先跑者输入读入与wall较慢，属于观察相关性，不能据此删负值或证明close不影响耗时。

最终使用显式`session-trim`，保持off及原session行为；NativeWorkspace策略不可变，只有带状/对角证明成功且策略true时close。下一dense重新分配的成本、close等待与释放都在execute总compute内；CLI的workspace_release_ms仍仅最终释放。borrowed输出已提前分配，共享owner也可能等待或被其他调用重新acquire，不保证同样RAM比例。

显著资源收益后一次集中验收通过65个API输出（7,554,056 B）、4项预期异常、6个小CLI/24矩阵（2,599,224 B）、3个大文件/7矩阵（4,268,828,856 B）。其中两个大文件复用已保留050筛选输出，最终显式策略最大流只运行一次。最终dense10000→band10000单次WS1531.953MiB、commit1531.055MiB、compute1258.11ms、wall3.652s；这是单次资源/正确性，不是配对速度结论。C真值的本地helper契约继续明确保留。

修复原默认构造的源码兼容后，没有重复大数值套：v1/v2共10个编译对象全字节一致，archive全部成员payload一致，EXE只有PE timestamp/checksum字段不同，实际产物没有重写或归一化。独立桥接报告验证完整差异范围，并通过3种旧式{}的严格编译及false/true策略控制。构造保持非显式零参数、显式布尔参数；source/core/CLI完整冻结与原数值gateSHA相连。

## S22：显式session的栈／控制流证明（03:24已安装）

以下为初筛及修复时的历史记录，正式集中验收和当前安装版本见本节末尾。

独立证明器从实际完整decoded PROGRAM的PC0/depth0开始，用有界工作列表验证33种opcode的栈效果、所有可达分支、目标范围、精确栈高合流和循环；未知、不同合流高度、栈深超4096、指令规模超100k或分析分配失败返回false，继续原检查路径。不证明数组索引或程序终止。只有immutable PreparedVM的call_once可认证，普通mutable Metadata/per-matrix不分析。被认证的threaded模板省掉重复pop下溢、NEXT溢出、PC和opcode边界检查；steps/lastPC、数组检查、初始化、Trunc、WRITE有限性、RETURN余额与原算术全部保留。

三源N7/M20000各模式三对、36进程，仅性能sanity：generic/deep-SSA/nested的session compute配对中位改善11.49%/0.51%/5.05%；per-matrix控制为−2.52%/+0.42%/+2.33%。至少2/3 session组达到5%且无超过5%中位回退，初筛通过。真实三份约40M–49M步的长流另36进程，session中位改善8.85%/4.25%/3.69%且9/9配对为正；per-matrix为−0.57%/+1.28%/+1.49%，长流计算护栏通过。进程wall负项和一次很大的启动差异全数保留，不称统一端到端提速。

静态certifier读取25份实际PROGRAM，全部返回stack证明成功；其中两份默认native不在执行路径上分析，不能称25份运行均启用认证。初始化证明计入vm_prepare/总compute，不保留额外按PC状态，decoded记录仍16B；最大100k PC临时向量上界约1.2MB，400k work保险在当前每PC一次且最多两条出边的实现中冗余，不虚构独立可达耗尽边界。

冷M1/M2另外36进程，generic的compute配对中位新增3/7us，deep-SSA为5/0us，nested为1/−4us；毫秒字段粒度1us，原始异常点和wall负项保留。显式batch收益不支持所有短流更快，更不支持自动session阈值。

独立静态审核发现初版证书bool公开可写，已改为private成员、只friend私有PreparedVMState写和readonly getter。修复前4源/3对象及产物冻结，重编3/3对象全字节一致，桥接原性能；mixed public/private后不保证standard-layout，代码没有offsetof/布局序列化依赖，本GNU编译的sizeof16断言通过，未泛化到未编译工具链。最新隔离CLI为`6e9325f8daf8ae776d2d249790be0b58a34ebd8ba09e422d187def3217c73679`。尚未执行集中正确性或安装，当前普通产品仍e47；下一步按冻结gate-plan一次验收。证据在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/frontend-vm/proved-stack/`。

S22最终集中验收一次通过：candidate与portable各934 opcode契约、53状态控制含512共享首次/热调用；portable+proved另934契约及27成功/27unknown形状；三版本各14,424额外payload/FP语义记录的hash一致，28 FP64 roundtrip。新增directed fixture各35个静态用例、34语义对照、22证明成功/13拒绝、2次独立分析分配失败及16次四舍入／sticky flags检查，静态proof保留包括INEXACT在内的所有异常位；runtime沿用已有计时导致INEXACT不可重复的限制，没有放松其余FP位。25份原C完整流317,488,564 B全通过，其中23实际VM使用session、两份native控制不构建计划。

两项实际CLI拒绝控制保留旧输出并移除partial。尾字节首次fixture期望错误文字与现有`unexpected trailing binary data`不一致，修正期望后两项通过；生产代码未改，原始错误日志保留。安全回归fixture已加入项目/CMake图，再configure/build证明CLI/core/flags完全未变，所以不重复数值套。完整204文件源码和全量build、原性能10对象/PE metadata桥接、私有写权限closure、数值gate及安装前27编译／回归输入核对连接同一收据。

2026-10-14 03:24普通CLI更新为`4cceb9db09eff01c7a93f17c1309d5a32dd2fdee2d5fee8ff70f573715c97092`，core为`9b9d3e8adb157ae612960c3000987aacd939e12e975881ef08989bc411a5caee`。只安装7份源码/配置/新测试，保留e47回滚。全局编译开关OFF，local-mingw ON，memory preset OFF；运行默认per-matrix。F已configure新flags，旧objects/test EXE仍不是本产品证据。上述“未验收／未安装”是初筛时的历史状态；正式集中gate和安装位于`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/frontend-vm/proved-stack/composition-gate.json`及`installed-runtime.json`。

原生串行closed-walk并非新方案。只读回看2026-10-10成熟报告：76性能进程、642原C比较case（418通用+224单worker FP）及30异常；AUTO单worker N4096/N10000耗时中位增加27.95%/7.83%，mixed增加1.73%，B32 N4096降低5.74%而N10000仅0.14%。当前walk主体与历史主体相同，storage已经变化，因此旧结果不冒称当前S22新测；仍保持OFF，不重编/重跑。该只读核对也确认当前default serial使用heap，而非walk。来源SHA、完整正负、当前源码/flags和0执行记录见`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/serial-walk-revisit/static-review.json`。

## S30：k对展开的调度限制与实际筛选

仅在S29两k之间加入GNU/Clang compiler-only空asm调度屏障，以8个accumulator的读写寄存器约束和memory clobber阻止下一k的因子load提前占寄存器；该屏障不发机器指令、不改变madd、尾或k顺序。其他编译器的源分支保留原未展开循环；只完成本次GNU构建，不宣称已跨编译器验收。真实代码已去YMM rsp spill，nonfused为51指令/2k（原等价54），fused为39（原38）；两者仍3整数rsp访存、无新call。CLI`f2e62f8d81652367cc1f568a6793513e793cf9ed50a19dbac991564b81de5aa9`，core`2731bac85d849afaceb0118c51ae73f979a5e3f9b2099bacb7d283beefcba742`，其他8个core成员及原main精确相同。

预注册5个nonfused主组：parallel16 dense4099/dense6145/mixed、default serial4099/6145，small1024和dynamic-FMA parallel16作控制；全7组各三对AB/BA/AB共42新进程，仅原样冻结C输入、输出长度和metrics sanity，无C数值比较。主组compute配对中位改善+2.71%/−6.17%/+0.29%/−1.46%/+3.98%，控制+3.06%/+0.38%。0/5主组达到5%，且N6145parallel超过全组回退≤5%护栏，失败，不扩数值验收、不安装，停止整个k-unroll方向，不再调N/参数/门槛。所有wall、首发异常、FMA单对−11.36%和其他原值保留；小路径未改，其正项不作为展开收益。证据在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/native-k-unroll2-barrier-screen/screen/report.json`及`native-k-unroll2-barrier/build-receipt.json`。

下一方向是整数位级融合全矩阵有限性扫描与lower带宽识别，先做隔离组件，避免带状/对角路径重复读约半个矩阵。必须完整检查upper/diag/lower finite、保留±0分类、超cap后继续验证余下元素；VM/stage/dense请求仍保留原扫描，暂不修改产品或宣称收益。

## S29：原生4行×8列内核按两个k展开

限定旧报告/源检索未找到同展开实验，已有3×12/6×8/row4/row8/row-pair属于不同变量。当前S22同源24编译输入，仅改变simd_kernel.cpp中既有非diagonal 4rows×8cols分支；先按原8个madd顺序完成k，再完成k+1，奇数尾保留，其他2row/diagonal/scalar路径、shape/tilesize和strict参数不改。CLI`375cb746cc1916d107d29a3c822ad56492596d020582ec8c1bce3c1ba1842ab4`，core`c930d50f6da0c7b13d9ab9aba4fb0601dca5bb99db39194ea3c090b9a2c7ccb4`，其他8个core成员及准确原main相同，未改F。

真实机器码pair-loop nonfused为16mul+16add，odd-tail为8mul+8add；Fused主循环16FMA、尾8FMA，guard保留，无新calls。但是nonfused原27指令/k变54指令/2k，新增8条YMM rsp spill/reload和3条整数rsp访存；fused19→35指令/2k，无YMM rsp spill但仍3条整数rsp。整体函数span5120→6272 B，rsp静态引用159→214；rbp在Fused循环是数据指针，不误算为栈。当前ROW_GROUP=0，只有logical_size>=2048、至少4row/8col且非diagonal触发变化，不能用小组件N测试未变路径来宣称收益。

据这一生成证据，原版未启动CLI/performance/数值验证，不把“循环次数减半”当收益。下一隔离修复尝试在两k之间限制因子load提前调度，同时保持每输出原k链，先看是否消除spill才决定性能筛选。构建/源码/flags/机器码证据在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/native-k-unroll2/build-receipt.json`及`machinecode-diagnosis/report.json`，原初机器码报告保留。

## S33：owned结构化原地分解，已安装

以准确S22 `4cce…7092` 为基线，新的联合扫描加owned结构化复用候选 `912c9fec8ac5e1793d6217afc5c3b09f49a8b8e536f273eeaef9b94a69072eba` / core `e7c9dd7fa08ecff90318762fd3bef95e816f7918e85e9ec2274bebca21c3b3c6` 已于05:55安装。它是两个功能的组合对照，不能把比例分拆为单特征因果收益。只有真正owned且延迟输出分配的native tiled调用，在完整有限值／结构分类后原地运行原i/j/k数学体，保留offband±0，成功后upper清+0再swap；借用/stage/VM保持其原分配行为。全局两个新开关OFF、local ON、memory OFF；默认serial1/per-matrix/native-workspace off不变。

预设至少3/4主组compute中位减少10%、所有组回退不超过5%；11组各三对AB/BA/AB共66实际CLI，Win32同监测方法采样20ms、无warmup，全部首发／wall／负项保留。四主组12/12compute配对正，均过门槛。

| 负载 | compute中位下降 | wall中位下降 | peak WS中位下降 |
|---|---:|---:|---:|
| diagonal4096，默认serial | 80.55% | 11.95% | 48.94% |
| diagonal10000，默认serial | 81.35% | 16.51% | 49.82% |
| band7-prefix4096，默认serial | 76.46% | 15.32% | 48.94% |
| band7-10000，默认serial | 82.16% | 25.23% | 49.82% |
| band7-n193/M1000 | 23.15% | 1.38% | −0.43% |
| dense4099，默认serial | −1.98% | −1.41% | 约0% |
| dense6145，默认serial | −0.29% | 1.47% | 约0% |
| dense6145，显式parallel16 | −4.11% | −0.86% | 约0% |
| band7-prefix4096，显式FMA | 77.90% | 14.91% | 48.94% |
| generic N7/M20000，per-matrix | −2.30% | 2.62% | −0.32% |
| generic N7/M20000，session | −1.28% | −8.48% | 约0% |

实际band10000三对baseline compute242.091/271.134/298.240ms、新48.163/48.380/52.093ms；峰值WS约1531.35→768.44MiB。peak commit下降约49.97%；WS/commit为Win32进程峰值计数，PrivateUsage为采样峰值，宿主共享负载单独记录，不能合称RSS或稳定官方预测。diagonal4096首发wall−66.80%及generic session wall负项保留，不由compute推断全程序一致提速。借用API与普通dense没有这项资源结论。

显著后一次集中验收完成：33份本轮候选完整输出共9,165,240,204 B。每组首输出直接对照整份期望字节，其余两份全SHA/长度对齐该已接受输出；band10000、dense4099、dense6145 serial/parallel使用真正缓存原C整流，其他明确分为原C leading-principal派生／精确记录重复、独立4I解析真值及FMA同输入S22基线。没有新最大C生成，没有重新执行这些大矩阵。2个新路径CLI失败保留已有输出并清partial；两版各539 API调用（每版461成功/78预期失败，14,127,740 B全payload对齐），borrowed只读、owned pointer、upper/±0、错误优先、四舍入×四FTZ/DAZ、workspace/session/trim/并发均过。API计时保留raw flags，28差异仅原有INEXACT；独立扫描2,188用例×32环境=70,016 actual调用（大N尾部128次），含预置全部异常标志，ALL flags/round/MXCSR均保持，OS只读payload与尾guard通过。facts匹配单测不替代实际runtime fallback，两者由不同分支分别覆盖。

三种完整配置真实compiled/executed：两新flag OFF、实际memory preset、同x86宿主CHOL_BUILD_X86_SIMD=OFF且两新flag ON，共12原C小矩阵和3失败清理通过；最后一项是编译出的标量回退，不是ARM机器实验。主205源码候选增加独立扫描回归、扩展既有所有权回归和注释／测试图，最终206源码fresh build的9实际core对象、main、flags及全PE有效bytes与原已测产品相同。首次脚本误要求整个.a SHA相同，被库头构建日期拒绝；保存原收据并只解析/归一日期完成桥接，无重编重链。PE只外层时间戳/校验和不同。交付原样已测912c/e7c，额外仅一次32 API调用的新增局部strict C-fixture回归，无重复大数值套；此局部fixture不冒称官方转录C。F已经configure，新测试已登记；旧F对象和测试EXE仍不能证明当前产品。

证据根 `G:/Hackathon-stage2-artifacts/project19/20261013-overnight/structured-owned-reuse/`：`screen/report.json`、`acceptance-streams/report.json`、`acceptance-api/report.json`、`classifier-gate/report.json`、`acceptance-config/report.json`、`regression-source-bridge.json`、`composition-gate.json` 与 `installed-runtime.json`。S32负结果不覆盖、不删除；接下来继续按实际剩余成本推进至09:00。

## S31–S32：合并有限值检查与带宽识别

S31使用独立非LTO编译单元，把全矩阵有限值验证与下三角首个非零识别合并。原finite/first_nonzero调用来自准确S22 core，计时前完成读取与分配。四个结构化主组各三对AB/BA/AB，含small193、dense4099/6145控制，共42进程。diag4096、diag10000、band7-prefix4096、band7-10000的扫描耗时配对中位下降48.53%、42.48%、44.41%、42.17%，12/12正项；控制分别+4.00%、−0.38%、−1.25%。组件门槛通过，但没有数值、fenv或整CLI验收。4I为新性能输入；principal-prefix由冻结输入原始行字节截取，有新shape/header，没有新原C oracle；原band10000和dense控制未改。

S32在独立205源码fresh构建中集成同一函数体，CLI `7d10f3ed9c8640ba064654b0bd90569486f33a1ae91f6c7923b10658c12f55c0`，core `dc65bc10123f861263b89905e0c4e435eab2060b57f0c0f694e676447abdc27d`。5/9其他core成员及准确G冻结main相同，strict参数保留。有限值检查仍在原错误优先位置；只有已识别native tiled请求做联合扫描，调用内facts绑定pointer/N/cap，dense超cap仍完整检查后续finite。联合时间全部计入input_validation_ms，不重复计入structure_scan_ms；分项范围变化不能替代compute收益。

预设四个主组至少3组compute中位改善5%、全部组回退不超过5%，11组各三对共66次完整CLI。diag4096、diag10000、band7-prefix4096、band7-10000的compute中位分别+0.32%、−5.53%、+15.82%、−4.16%；只有1/4达标。small193/M1000为+0.54%；dense4099/6145默认serial为−2.31%/−3.14%，dense6145显式parallel16为+0.41%；显式FMA band4096为+6.28%，generic N7/M20000 per-matrix/session为−1.42%/−0.99%。扫描下降在真实CLI复现，但总计算门槛失败；所有首发、wall和负项保留，不扩大正确性、不安装。下一独立候选研究owned结构化输入原地分解，减少整输出分配、清零与下三角复制；旧候选与报告冻结。

证据分别在 `G:/Hackathon-stage2-artifacts/project19/20261013-overnight/fused-finite-band-scan/screen/report.json` 与 `.../fused-finite-band-runtime/screen/report.json`；新候选不得继承组件收益或假定数值已验收。当前安装仍是S22 `4cce…7092`。

## S27–S28：分派尾部代码生成

S27唯一增加`--param=max-goto-duplication-insns=64`，compiler -Q确认默认8、请求64均exit0；不是参数传递错误。新threaded对象与已安装原对象逐字节相同，全部9个core成员及原main相同，两个栈模板仍各6分派点，所有PE section payload也相同，仅外层时间戳/校验和不同。初始桥接脚本要求恰好一成员改变，因changed=[]触发断言，读原.a最终核实为无变化，不重编或链接。保留失败收据，补完整静态收据；没有性能/数值运行，没有扩大参数网格。证据在`.../frontend-vm/threaded-goto-dup64/parameter-evidence.json`及`build-receipt.json`。

S28唯一对原S22 threaded TU增加`-fno-crossjumping`，原O3/gcse/strict/goto参数保留。真实间接分派点两模板均6→33，函数大小15968→17056 B、8240→9968 B；proved-stack静态rsp引用230→260，未认证栈264不变。CLI`82eb89f279f4ac3332c02949bf06bfd19fba19d32a4ed4884e0238203314cd86`，core`1052dc5eff53cee20fdb30a628e6f9e98dc6282ac3d8be065d5a255ece388f4a`；源码24份、其他8个core成员和准确G冻结main未变，不含数组证明。

同S26三受益源两计划和unknown/native控制各三对，共48新进程，仅长度/steps/plan sanity。session generic/SSA/nested的compute配对中位改善−0.39%/−0.17%/+3.99%，per-matrix−3.35%/+0.89%/−1.21%；unknown/native控制−1.23%/−4.50%。没有任何受益session中位达到5%，未过门槛，不扩大数值验收、不安装。nested三对正项、首发wall异常以及所有负项均保留；分派点增多没有产生普遍显著收益。停止本批编译分派参数实验。证据在`.../frontend-vm/threaded-no-crossjump/screen/report.json`及`machinecode-diagnosis/report.json`。

## S26：线程VM单TU关闭gcse

与当前4cce/9b9的源码/24份相关编译输入逐字节相同，只对threaded TU增加`-fno-gcse`；其余strict参数保留，不包含数组证明。精确安装G core只换1/9成员，其余8和原main相同，未使用F旧objects。CLI`18fadb991af907b24ed5631d342de84cc2a122c76a4d2b722714c0e6e0d40ea4`，core`b6acb1030a7064c0d7d6a997e8e503876b8efe87dd1647c8fbc61cbcbb0f7261`。机器码未认证栈分派站点6→5、认证栈仍6；函数体大小15968→16000 B和8240→8240 B，仅是生成证据。

generic/deep-SSA40/nested-rect三源N7/M20000各per-matrix和session，unknown/native作session控制，三对AB/BA/AB共48实际CLI进程，原C冻结输入记录只原样重复，不重新生成或数值比较。session compute配对中位改善−22.41%/−3.44%/−6.46%，9/9回退；per-matrix为+0.58%/+0.61%/+0.13%，unknown/native为−10.71%/−1.26%。未过2/3 session至少5%、控制不超过5%回退门槛，停止推广，不扩数值、不安装；所有首发wall及负项保留。报告沿用旧脚本variant标签`array`，在本阶段仅指编译flag候选，实际没有数组认证。GCC文档提示不是本机速度证据。证据在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/frontend-vm/threaded-no-gcse/screen/report.json`及`build-receipt.json`。

后续S27/S28依据[GCC15.2优化参数文档](https://gcc.gnu.org/onlinedocs/gcc-15.2.0/gcc/Optimize-Options.html)进行独立构建/筛选，结果见上文；未将文档描述当作性能结论。

## S25：原生heap任务行优先筛选

以当前4cce/9b9为基线，仅tiled对象改变；两处lazy/full packed key由(col,panel,index)改为(row,col,index)，两个nonpacked比较器同步，其他8个core对象/main相同。依赖、通知、bucket、数学和geometry不变。同destination的更新panel顺序仍由DAG约束维持。核对安装flags发现当前没有SERIAL_TILE_WALK、LAZY_TILE_GRAPH或PACKED_READY_KEYS宏，实际运行full graph/nonpacked heap；默认单线程同样调用heap worker。筛选前纠正串行不走queue的假设，加入两个默认serial主目标，而非把串行称作不受影响。lazy/packed仅静态证据，可能首次异常来源变化未作新验收。

候选CLI`7c35357c9cde5283f4362ef0d21eccbfd8757c653cde373921bb66a4a35d01c1`。原样冻结C输入：parallel16 dense4099/dense6145/dynamic-plain、default serial4099/6145共五主组，parallel16 dense1024控制，各三对AB/BA/AB共36进程，仅长度/metrics/geometry。主组compute配对中位改善分别−9.20%/−10.51%/−14.01%/−14.56%/−8.22%，控制−2.29%。预设至少3/5主组改善5%、所有组中位回退不超过5%，未通过，停止不扩大数值验收、不安装；所有wall和首发异常保留。行优先并未产生本机总收益，不能从lookahead设想推断性能。证据在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/native-row-ready-screen/screen/report.json`及`native-row-ready-key/build-manifest.json`。

## S24：owned输出上三角清零合并进分行导出

当前4cce/9b9基线同源204文件；只替换tiled对象，其余8个core成员和main逐字节相同。输入全部worker读完成后仍swap给output；将upper +0 fill合并入已有export_rows，每个物理row唯一owner，下三角从独立packed factors导出。借用输入、结构化路径和非column配置保持原路，没有改几何、数学或线程阈值。候选CLI`d8f032be6f7f3ea28bf1a1edd1f1c0b5e0c1e7fd8b0765d15eadfc50b4518084`，未安装。

冻结原C输入，不再生成C或比较数值；dense4099、dense6145、dynamic-plain显式parallel16三组为受益组，默认serial4099及parallel16 dense1024为控制，3对AB/BA/AB共30实际CLI进程，仅长度/metrics/geometry核对。总compute配对中位改善为+0.17%/−2.57%/+5.68%，控制−3.81%/+4.94%。只有1/3主组达到5%，未过预设2/3门槛，停止扩大正确性验收，不安装。parallel受益组export分项每对改善15.90%..40.17%，不能用分项代替总compute；旧新export_ms都覆盖swap、清upper和导出，input_recycle_ms从swap+fill变swap-only，范围变化不作为收益。首发wall异常、所有负项和small1024的wall中位−11.80%全部保留。证据在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/native-upper-zero-screen/screen/report.json`及`native-upper-zero-v1/build-manifest.json`。

## S23：数组下标证明的独立静态阶段

独立A0/A1 certifier只读取真实PROGRAM，不执行VM/原C。25流（19源）共认证38/115个静态READ/WRITE PC：8流A1，以及两份unknown-data-step各1个常量A0；fresh-dependent为4/5，idx-1仍checked。最大观察work31,028/250,000，decoded16B，25流所观察的fenv/rounding未变。独立静态审核未找到不安全认证反例，但不将census作为健全性验收或提速结果；A1自身不证明循环栈安全，不能替代S22证书。

实现要求实际CFG两分支／侧入口、kill全部loop写槽含guard使用的N² alias、唯一正步长和真实i<N²守卫、全合法N/block域的精确整数关系，以及预算/分配失败全部unknown。认证位private、仅不可变State发布。初始旧e47集成未执行；随后已在G重新合入S22，保持两种独立证明和原错误/PC/steps/数组表达式，实际短筛负结果见下文。普通产品无数组认证功能，未修改F。证据位于`.../frontend-vm/bounds-proof-candidate/census.json`及`independent-review.json`。

S23在S22基础上的实际runtime短筛已完成：493文件完整G构建，CLI`a7f4ae33d4d81793fde28a2c3bfbdd49839e6f0b1aa7fbecafc996ca6e3788b0`，core`0e11bb5ae400514fb4df3037b289bdb0e9adcea28a6cf6391587e419ec9f09bb`，对当前4cce基线。保持stack证明，新增独立array可用标志及四种模板组合；只有首次threaded消费者才在call_once内生成数组证书，首次decoded/tos2消费者之后不追认、不修改已发布计划。并发不同首消费者可以有不同优化可用性，不承诺性能一致。无数组PC认证和普通per-matrix不包含per-access标志检查分支，decoded仍16B。

固定六源N7/M20000，三源分别per-matrix/session，另外低覆盖unknown、无覆盖rect、native只作session控制，共9组×3对=54进程。输入为冻结独立C输入中同一合法N7记录原样重复，仅重写M计数；筛选只查长度、矩阵数、steps和计划复用，不作新原C输出比较。generic/int-conversion/helpers的session compute配对中位为−12.88%/−5.65%/−12.69%，9/9对回退；per-matrix为−0.11%/−3.51%/−0.55%。unknown/rect/native控制为−0.82%/−0.94%/−2.10%。主门槛至少2/3 eligible session组改善5%且所有控制无超过5%中位回退，结果未通过；停止扩大验收，不安装，所有wall正负样本保留。

nm读取实际构建的StackProved=true函数：旧体0x2030 B，新array-disabled仍0x2030，array-enabled为0x2020，略小并未带来提速。下一步仅静态机器码诊断flag分支／dispatch／寄存器，证明器不因负性能改动。参考[GCC15.2优化文档](https://gcc.gnu.org/onlinedocs/gcc-15.2.0/gcc/Optimize-Options.html)中computed-goto与gcse的提示，只作为研究方向，不当作本机收益证据。原源码、flags、命令和全部样本在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/frontend-vm/bounds-proof-s22/screen/report.json`。

S23执行路径修复另在`.../frontend-vm/bounds-proof-vector-index`冻结：只替换threaded对象，其余9个库成员和main逐字节相同。helper传vector引用，认证值按全合法N域由uint32转size_t；证明器不变。机器码确认认证READ不再重复载入输入指针，vector.end只在未认证分支载入，认证READ/WRITE跳过2^63转换分支。静态诊断parser另有续行字节计数更正：旧/new array-false正确指令数3346/1649，归一化零差异和6间接dispatch站点结论不变；不是完整产品或速度等价证明。

修复版CLI`9969f962bc903ec6828521cb62d02d874a18b3c69941ca454ddbe33cde9da3f2`对当前4cce重做同一预注册9组×3对，54新进程；不重跑旧候选。generic/int-conversion/helpers session中位compute改善−13.51%/−3.69%/−17.18%，9/9回退；per-matrix为−0.18%/+2.34%/+0.66%。unknown/rect/native控制为+0.98%/−6.88%/+6.20%，native漂移亦全部保留，不用它作数组收益。未达到显著门槛，不扩数值验收、不安装。更少加载和转换并不保证总执行更快；下一独立候选将认证READ/WRITE分派到私有handler，以消除每次访存的认证条件分支。原Metadata/wire/公开Opcode及证明域不得改变。

S23第三个独立执行候选使用offset7 private uint8 tag，将认证READ/WRITE分派到独立33/34 handler，普通Opcode/wire不改，offset6仍private可用摘要。State在call_once发布前为所有PC设置完整normal/invalid/tag，portable和首次decoded消费者不追认；数组proof原SHA不变。全493源码freshbuild；初稿同时外层定义33/36 target表，使GCC把unused certified label也保留在Arrayfalse，修正为if constexpr内独立表后才筛选。初稿CLI62c1未运行，源码/asm保留。最终CLI`aeaf10ce7f31f94eca81925434813c54ab693f347393047e359e459a60cdf34a`，core`0fafe39e216ff706becd652bb77430906f57062bbfee16799472cc4b21e4b06b`；Arrayfalse函数大小恢复，StackProved=true归一化相同，false-stack仍有121行加载/排布差异，不作整产品等价声明。四体仍各6间接站点，认证handler没有bool检查/size载入/2^63转换分支。

同一预注册九组三对54新进程对当前4cce，generic/int-conversion/helpers的session中位compute改善−3.63%/+1.32%/−2.71%，只有int-conversion两对为正；per-matrix为+5.12%/+0.99%/−0.18%。unknown/rect/native控制−4.41%/+4.62%/−3.33%。显著门槛未通过，停止三个数组执行候选，不扩QA、不安装，不因局部per-matrix或wall正项宣称数组证明收益。证据在`.../frontend-vm/bounds-proof-private-opcode/screen/report.json`、`build-receipt.json`与`delivery-freeze.json`。

## S21：PreparedVM发布快径筛选

独立候选在私有State中以atomic readiness和mutex替代call_once：构造线程在vector完整生成后release发布，热调用acquire读取；冷并发锁内二次检查，构建异常不发布，下一调用可重试。每调用fresh frame及mutable Metadata接口保持原路径。只替换runtime对象，未组合S19/S20，也未改F生产源码。

三源N7/M20000，两计划模式各三对，共36次实际默认auto CLI长度/steps筛选。generic、deep-SSA、nested的session compute配对中位分别+2.72%、−1.40%、+3.92%；per-matrix控制分别+0.34%、+1.87%、−1.09%。预设至少2/3 session组改善5%且无超过5%中位回退，结果未通过，停止扩大。保留首发wall异常、SSA全部三对session回退和全部原值；不从减少同步调用次数推断实际收益。没有新集中数值/并发验收或安装，证据在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/frontend-vm/lazy-mutex/screen/report.json`。

## S19–S20：标量初始化存储筛选

两候选都以当前e47 CLI/6f6 core为基线，单独替换threaded VM对象，原main和其他对象保持基线；默认auto后端，三源N7/M20000，per-matrix及显式session各三对AB/BA/AB，每候选36进程。只核对输出长度、steps及模式，不进行新原C数值比较。预设至少4/6组中位改善5%、所有默认per-matrix组中位为正且无超过5%中位回退，才能进入长流护栏和集中验收。

S19将`vector<bool>`初始化位改为字节向量。generic per-matrix/session中位compute改善3.85%/6.10%，deep-SSA为3.15%/3.15%，nested为3.12%/1.66%；17/18对为正，但仅1/6组达到5%。nested session的进程wall中位为−2.03%。存储由按64位取整的bitmap增为每槽1字节，最多4096槽。未过显著门槛，不推广、不扩大验收。

S20进一步将标量double和尾部初始化字节放进同一个double向量，尾部double只通过unsigned-char对象表示访问，从不读取其数值，长度加法有溢出护栏。减少一次frame分配，但generic per-matrix/session中位compute为−4.49%/−5.91%，deep-SSA为−3.48%/−2.07%，nested为+2.07%/+0.53%；不能用“分配次数减少”当作提速证据。全部样本及首发wall异常保留，停止候选，无生产修改。证据分别在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/frontend-vm/byte-initialized/screen/report.json`和`.../compact-frame/screen/report.json`。

## S18：有限值扫描循环展开筛选

当前6f6 core的实际`all_finite_avx2`符号与单独替换SIMD对象的候选，固定N3/1025/4099/10000各三对交替、24个独立进程。候选将四个4-double向量检查合并为一个16-double循环判断，严格浮点构建参数不变。分配与填充在计时外，每进程扫描约250M个值；这是组件筛选，不能称CLI或总compute改善。

四组配对中位扫描时间减少分别为−10.20%、+2.07%、+5.77%、−4.91%，改善对数0/3、2/3、2/3、1/3；N4099单对范围−15.64%至+8.22%。最大形状回退且收益不稳定，停止候选，不扩大正确性验收，不修改生产源码或产物。原值、候选源码、构建参数及产品SHA保留在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/finite-scan16/screen/report.json`。

## S16–S17：保留默认与负实验

同一个已安装1af运行文件，三源N3/N7、M2/M20000、两对AB/BA共48进程，不改源码、不编译，只做长度/steps及模式计数检查。M20000六组compute均两对改善：generic N3/N7为10.89%/5.54%，SSA为9.10%/4.34%，nested为20.83%/7.61%；每流计划构建20000→1，prepare/setup/final release全部计入。M2六组全部两对回退，每组额外约13–22μs，因此“所有M>1自动复用”未推广。进程启动wall异常（含一次2.221s而compute仅0.058ms）和大流wall负项保留；M2微秒数据受0.001ms报告精度限制。默认per-matrix与显式session不变。

优先级守卫的eager heap U→U直接领取后继候选，保持所有factor依赖、锁外计算及completed/error屏障；不叠加已拒绝的lock-reuse。18次固定CLI、三组各三对仅性能sanity：N1025/N4099/mixedM的compute配对中位为−2.55%/−0.23%/+4.9385%，最后一组波动−9.0%至+15.25%，未达到预设5%门槛。未扩大正确性，未安装；4.9385%不能四舍五入当作通过。全部源码、flags、原值及负结果冻结在`G:/Hackathon-stage2-artifacts/project19/20261013-overnight/scheduling/direct-successor/manifest.json`。
