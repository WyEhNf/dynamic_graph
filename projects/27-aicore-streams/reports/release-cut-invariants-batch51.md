# R51静态不变量审查

`completed/users/degree/live`始终表示已完成的原始执行前缀：users是原DIRECT尚未完成用户计数，degree是未完成直接前驱数。live包含所有仍有用户的已完成输出和所有sink输出。probe临时复制这些状态，外部实际前缀不受失败probe影响；只有完整合法probe的真实order才逐节点apply到实际前缀。

闭集C从p的全部尚未完成原DIRECT用户向原祖先递归构造，done前缀在边界停止；原DAG保证C存在拓扑序。不按workspace target筛选用户。probe结束必须`users[p]==0`，才证明p输出已经按原生命周期释放。C中其他输出对外部用户或sink的持有继续纳入最终live。`final_live`是串行递推的终端清理前记账；若C恰好完成全图，无后续分配，整体sink在T的最终清理不影响已测峰值。

每次实际分配先以capacity-live的剩余额度检查W与O；检查成功后live+W+O至多INT64_MAX，才计算峰。释放的父输出互不重复（Graph拒绝重复inputs），且为当前实际持有输出的子集，故freed累加不超过live、不溢出。`O-freed`范围[-MAX,MAX]，W+O优先级饱和不参与实际释放。新102控制同时检查MAX恰好可放与超过MAX非法；候选的完整运行还需独立事件模型/原deadline核验，cut成功本身不是全图/截止证明。

safe ready节点的净变化O-freed<=0且BEGIN可放，因此可提前完成：释放的父输出只有该节点最后一个尚未完成原DIRECT用户，后续原任务不需要这些输出；新输出不大于释放量。DAG前置条件不受损，后续显存持有不增加。sink新输出仍被保留且包含在O中。这一论证用于串行Compute顺序，没有推广为多流Event交换定理。

计费默认总16M：新cut以checked remaining budget方式最多计2M；原R48使用余量至少14M。原识别k<=512、n<=4096；pair阶段最多1M，12条亲和序列每次至多4个recent、每轮至多k²探查，宽松上界48k²，完整小组用户探查最多4n。因此原profile之前计费上界13,599,296低于14M，不会触发其`++work>limit`的单步越界；profile/move在unit分配前检查剩余预算。原种子/阈值保持，默认实际67诊断最大15999933。这个证明针对公开调用的默认16M；private search helper任意极小自定义预算不属于提交接口，不能据此宣称任意helper limit的同一性质。

16M是可复现搜索计费模型，不等价CPU周期、墙时或隐藏判题器资源限制；历史投影预处理口径保持。probe内部单一greedy次序、128节点/24producer门槛及cut2M预算均可能错过合法顺序。剩余57原图+6持出仍已知可行，失败不构成不可行证书。
