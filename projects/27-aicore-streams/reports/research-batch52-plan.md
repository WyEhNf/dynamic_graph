# R52静态归因与下一单项候选计划（未执行求解）

当前默认R51的57原困难+6新持出共63个未解记录，全部原硬件/节点/原DIRECT边/deadline被复制到`research/batch52/remaining63-input-only.json`。只读取当前结果的pass标记进行审计选择，然后仅复制name/hardware/nodes/deadline/expected-feasible；不复制或使用witness、generation、计划顺序。实际静态分析脚本exit0，没有编译、调用solver、重放前缀或运行性能。

63图均n<=4096且串行Compute总时长不超过deadline；37适用旧projection，8超过512target，18低于target2门槛。合计1789个indegree=outdegree=1内部节点。每个具有非零O的非sink producer p，求所有原DIRECT用户的完整原祖先并集C，然后去除p和p全部祖先。任何p已完成的真实DAG前缀中，p祖先均已完成、剩余DIRECT用户只是原用户子集，所以实际cut一定是此C的子集。**28图中所有producer的C均<=128，故R51的128节点门槛无法解释这些图的失败**；这个结论只排除门槛，不证明内部greedy一定失败，也不排除预算耗尽、外部live或选择错误。

另外28图至少一个producer有超过128个“立即完成p后必未完成”的descendant祖先闭集节点；没有图所有producer都如此。这个下界只对p刚完成、descendant尚未执行时成立，后续用户/中间节点执行会缩小cut。不能把它标作实际全流程cut拒绝、不能据此扩大128门槛，也不能称图不可行。其余静态特征和逐producer上下界见`reports/remaining-static-classification-batch52.json`。

下一步首先拟做**单独归因诊断**，不改变生产默认或搜索路径：在R51隔离副本用observer计数及保存首个terminal-prefix（done/users/degree/live），区分图门槛、整cut>128、实际ready为空、ready存在但BEGIN容量不足、完整cut无净释放、外部用户/sink持出、cut2M耗尽及旧投影余量耗尽；同时保存每个probe的完成/拒绝阶段。observer写入不计作搜索预算、不得改变比较器/tie或返回order，先用少量完整小图比较原/observer所有输出和chargedwork恒等。这个诊断尚未编译或执行，需要父任务批准小诊断，禁止直接whole/performance。

最有依据的单项下一算法是**内部cut首次停滞时有界frontier回退**：只对<=128完整cut、真实ready存在但全不fit的已保存状态，尝试撤回最近1–2个正净持有节点并选择另一个同前缀ready分支；所有状态包含完整原done/users/degree/live，重新检查每BEGIN W+O/最后DIRECT END释放、cut外用户和sink保留。它在原cut2M配额内部消耗现有预算，不增加128/top24/种子/16M总额，也不改变旧R48fallback。暂不实施：先要求observer证明真实失败图确有此类greedy停滞，再构造完整原DAG反例和独立bigint金标，显示分支可行而当前单一greedy失败；若真实主要原因是2M耗尽或不可放的必持出，这条方案不应盲推。

小控制须覆盖：两ready中较小净O诱发下一步阻塞但另一顺序可行、共享父输出只有最后DIRECT用户释放、多个root/多个sink、cut外用户、交叠组/依赖交叉、O=0/W=0、恰好MAX与超过MAX、相同score tie、无替代ready、预算边界，以及撤回不改变前缀外消费者状态。归因不等于不可行证明；新候选必须先有真实原失败恢复，之后才申请完整功能和同Release成本窗口。

完整手算草稿见`research/batch52/hand-frontier-counterexample.json`：P输出50，两个DIRECT用户A输出20/workspace0、B输出30/workspace20，全部exec1，原容量100/单AIC核/deadline3。P完成后当前净O准则选A20在B30前，ENDlive70，B下一BEGIN要求120而拒绝；撤回A改B先执行，三次BEGIN为50/100/100，ENDlive50/80/50，最后DIRECT用户A完成释放P，两sink合50保留到T3。B本身的必同时存活50+20+30给出100必要下界，所以这个完整手算可行peak100达到控制最优。它证明内部单greedy有局限，不证明整个默认求解器会在三节点图失败；一般调度启发式可能已解决它。草稿尚未执行任何模型/测试，后续独立gold及诊断须按授权门槛完成。
