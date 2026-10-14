# R48 成组消费者移动：新增一例恢复的隔离候选

以下初始构思在静态阶段写成。其后实际诊断与完整质量结果另列于文末；候选未推广、未做性能测量，默认 R45 冻结源未改变。不得把初始收益预期当作实验结果。

候选从 R45（保留原先非约束 affinity seeds）构建，未合并负结果 R46 阈值或 R47 ready-affinity。识别只看原始 DAG：非 target 且 O>0 的 producer，其全部直接消费者必须是 2–4 个 target。按消费者集合聚合 producer 输出作为排序权重；权重可饱和到 MAX，但实际 profile 使用独立宽整数，实际计划仍经精确容量、时间、Event 与 deadline 校验。任何不在集合中的直接消费者都使该 producer 不参与分组，没有提前释放输出。

在单节点局部移动停滞时，按共享输出权重尝试最多 24 个覆盖当前 critical 位置的组。组成员保留原 permutation 的相对顺序，移到 critical 附近两个边界；原接口偏序的 Kahn normalization 与祖先 closure 仍决定最终执行顺序，跨组依赖不能绕过。重叠成员的组分别尝试，没有融合节点或删除边。仍然最多两个种子、64 次局部迭代及总 16M charged-work 上限；额外 group 识别的直接边访问也计入该上限，不能声称所有预处理或 CPU 指令均受此计数覆盖。

收益假设：共享大输出的若干消费者可能只有整体靠近才能跨过严格单节点局部最小值。已有 closure profile 能精确判断这项假设，候选没有把“共享 producer”推导为无条件优化保证。额外搜索可能占用原先第二个种子的预算并损失恢复，因此必须保留 R45 的两例恢复、完整失败记录以及新增持出六图，不因小金标正确就推定质量改善。

准备的独立金标 `scripts/make_group_gold_batch48.py` 用原始直接用户集合识别组、用前后边界切片定义 stable block insertion，并调用完整祖先集合与 prefix/future live-set 的 Python bigint reference。显式控制含成员重叠、组间依赖交叉、重复用户集合的权重超过 MAX、O=0、多个根/sink、最后 DIRECT consumer 释放及瞬时 profile 超 MAX。金标测试模板是 `research/batch48/test_group_template.cpp`。

预声明流程是在协调的 R45 性能窗口结束后，先一次执行 group 金标与原 495 profile 控制，再一次执行旧 61 和新 6 失败诊断。仅有真实新恢复、保持原恢复且独立校验通过，才扩大到完整原 202 和持出 48；若仍 2→2/0→0 或出现丢失，则保持为负结果，不推广、不为它添加普遍预算。R45 的同 Release 成本与晋升判据另行处理，不混入此候选因果比较。

## 实际阶段结果（待完成候选数值/构建门槛）

首编译漏加 `<map>`，实际编译失败与日志保留；添加标准库头后，三个功能 EXE 的顺序构建 session75690 actual exit0。实际完整源 **da5dc93e1f0615e0e1a3e4daf1f349eb9fe6d275cbff843d85cbb6da05b178c3**；片段已完整展开，不增加提交依赖。金标生成没有基于求解器结果删图：83 recognition cases、210 moved profiles，其中58是无安全组的负控制；原495闭包控制也实际通过。

原R44的61失败输入（含此前R45已恢复两例）中35投影适用，恢复 **2→3**，保留原两例，新增 `irregular_consumers_local_k24_ret1_seed20273418`，131节点，串行 **T2421486微秒、peak1946字节**。新持出六个失败输入投影适用5，仍 **0→0**，没有新恢复。31原诊断与4持出诊断标记预算耗尽，不能称它们不可行。

三份真实返回串行计划逐原ID恰好一次、原始偏序、两核池、每BEGIN的W+O、每END最后DIRECT用户释放、sink保留、容量及deadline，用独立Python bigint prefix/future live集合重新计算全通过。输入与原hard202的hardware/nodes/deadline完全一致，传入solver的版本无witness/generation。完整诊断冻结 `research/batch48/diagnostic-checkpoint.json` SHA **e23d21950e7a7b36bfc3472fbebf9d1fc1ab418b75684a23f26c6a3e216324be**，另存实际三输入与三输出计划，原诊断/witness历史都保留。

因实质新恢复才运行全量功能：session24872 actual exit0，原202 **143→144**、共同143的T/peak全同、0丢失/分歧，剩58；新48 **42→42**、共同42的T/peak全同，剩6。两份完整raw和失败费用保存在 `reports/functional-summary-batch48.json`，O2共享功能不作速度结论。

session47995 actual exit0，979原始记录对R45逐条name/pass/valid/T/peak全同；132外部审计、36结构、72旧持出和12资源族实际通过/质量全同，见 `reports/full-verification-batch48.json`。

镜像Release **13/13 CTest** actual通过（6.62秒功能墙时），测试源码直接include路径均重定向actualR48。此后cmd启动Clang时相对路径正斜杠被cmd当作选项，包装进程57455 exit1，在Clang启动前报`research not recognized`；改为Windows Path字符串，单独 `--clang-only` session52945 actual exit0，不重新运行已通过的Release/CTest。UCRT LNK4217链接警告与runtimeUB分开记录。

三份新Clang EXE真正包含同da5dc源；**523固定plan+495workspace profiles+83recognition/210group moves**一次新运行全通过，0runtimeUB。默认GCC评分20180及浅层2590控制由镜像CTest实际运行。完整候选验收冻结 `research/batch48/acceptance-checkpoint.json` SHA **67790b5804a2440acd21b9646ce38184b2b4164bc12c38c0646a8266b909aec4**，实际Release archive **991e18cdde3d7e803bc7a10c6d5e2910312e8485417eceab01c6767a717dfd64**。

性能先声明：`research/batch48/paired-plan.json` SHA **e034ca827207af7eb57842313f3a3372d682e2797f69fba5afb6d36908ab1b56**，R45实际默认archive5acc与R48 Release991e，完整202+48各三轮交替、全部失败保留；不能与R45上一性能实测3e827混称同baseline。此后经root窗口授权实际执行，声明文件不回写终态；实测见下节。默认仍R45的143/202与原59+新6共65未解；候选144/202只减少一条原未解、58+6共64，新的48仍无额外恢复，不宣称泛化成功或速度收益。

## 实际同Release费用终态（待root审核/默认未改变）

唯一实际 session65788 exit0，全202+48各三轮完整，脚本CLI wall185.2929215秒；未额外重跑。原202每轮143→144、143共同T/peak恒等、58共同失败、1恢复。全CPU比 **0.974586/0.996964/1.093806**，逐配对中位 **-0.30%**，独立两侧中位 **25.984375→25.765625秒/-0.84%**；第三轮 **+9.38%**，不声称稳定加速。求解wall逐配对中位-0.19%；CLI独立中位27.531782→27.650994秒、PeakWS最大316878848→317050880字节，包含数据/保存计划/验证，不是算法独占内存。

58共同失败CPU两侧独立中位18.375→18.125秒，费用全部保留，不能因它们仍失败而剔除。新48每轮42→42、6共同失败、0恢复，CPU比 **0.985294/1.061538/1.022901**，配对与side中位均 **+2.29%**，2.046875→2.093750秒；求解wall配对中位+0.72%。此批新48没有质量增益。

Win32线程CPU量化、OS干扰和不同中位口径均保留；trial host_busy/host_available RAM未采，用户后台应用不变，不能称完整hostload记录或整机空闲。`reports/resource-cost-summary-batch48.json`与`research/batch48/paired-completion.json`固定实际EXE/源/driver/全部raw数据SHA与费用；默认晋升须由root独立审计后决定，此时默认45不变。

下一方向先做一次58未解原图的input-only静态计数：32满足既有接口门槛，32均既有2..4组也有5..16完整DIRECT-target用户组，总大组2401，新增适用图0。`reports/large-group-classification-batch49.json`不读plan/witness、不删原root/节点、不改变硬件/容量/deadline，计数不是可行性证据。R49未生成求解源码/编译/诊断，待决定是否将组上限单改4→16；可能因为24-group优先级替代而丢旧恢复，必须独立测量。


第48批当前默认：保留R45接口/闭包/seeds/16Mcap，原DIRECT消费者2..4完整组在单节点局部停滞时有界移动，仅旧组合失败后触发；不读witness/名字/seed、不改边/释放时机。原202困难143→144，新增131节点独立原拓扑T2421486微秒/peak1946；共同143 T/peak全同、0丢失。新48保持42/48，共同42质量不变，6未解；原58+新6共64已知有解未解保留。合计1349记录1285按预期，含1预期不可行拒绝与参数重复，不是1285可行输出。

979原记录对R45逐条name/pass/valid/T/peak全同，36/72/12资源全通过、144最优审计/33证书。83识别/210组移动+495闭包+523固定plan独立Pythonbigint/新ClangUBSan全通过，实际默认13/13 CTest（2.80秒共享功能），2590浅层、20180评分金标也针对actual默认执行。9条行为烟测6成功（新131+旧2恢复+3正常）与3已知有解未解完全匹配候选；CLI预期1由wrapper确认并exit0，没有重新运行979。

唯一同O3完整202+48三轮，baseline actualR45archive5acc/candidateRelease991e：原202全CPU比0.974586/0.996964/1.093806、paired中位-0.30%、side中位-0.84%，第3+9.38%，不称稳定加速；新48 CPU比0.985294/1.061538/1.022901、中位+2.29%，无新恢复。全部失败费用保留；host_busy/可用RAM每trial未测、后台用户应用不变。原输入、plan、实际default/measurementEXE、flags、compile/test/generator/hash分别冻结 `research/batch48/provenance.json`。源 `da5dc93e1f0615e0e1a3e4daf1f349eb9fe6d275cbff843d85cbb6da05b178c3`，实际默认EXE `54fc7e9b2257f1edcd6925126f32e969826a5d6ba93bc2f9b3e8fd5dd5538c10`，测量EXE `991e18cdde3d7e803bc7a10c6d5e2910312e8485417eceab01c6767a717dfd64`。R45完整rollback在 `research/batch45/rollback/manifest.json`，旧R31打开报告不动。R49只静态计数58未解中32适用、2401完整5..16组，未编译新solver，未混默认。
