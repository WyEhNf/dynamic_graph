# R55 实现与金标冻结说明

候选只在 `research/batch55/solution.cpp`，当前普通默认8b7c和用户打开的旧TeX未变。尚未编译或执行C++候选；下文全是预执行参考/资格数，**不是160候选测试通过**。

160分母按已冻结六族48/32/32/16/16/16生成，158 producer eligible；2个故意 output=0 的原图控制明确 ineligible。8个C=129/130的控制依然 producer eligible，但超原128上界，whole提供计划全合法；不能把 cut 拒绝写成图不可行。127/128用真实5节点死锁骨架+P的零输出直接消费者，能够在 repair 中走到第二uint64和第127位。

16个非负int64边界控制包含物理MAX恰好可行、W/O和超过MAX、多个历史producer总和>MAX但实际峰值合法、外部前缀持出、sink合计MAX/超过MAX。所有单项仍在int64范围。prefix始终是原DAG ideal且独立bigint物理合法；固定whole计划有138合法、22预期非法，非法不能计为可行输出。JSON driver输入只含int64单项，没有gold中的>MAX bigint求和值，避免本地int64解析器误读gold字段。

参考release_probe预期116 valid、12 exhausted、102触发repair。这些只是Python预执行参考。另16个same-mask/宽容量控制中，生产greedy已经成功并必须保留旧order；为了实际测试两条合法cut路径到相同mask时只保留较低peak，driver另作16个**直接repair routine单元断言**。因此160控制将有160正常probe、16直接routine、160独立fixed-plan physics检查；这16次不是新增生产应用或质量恢复。

精确账表另存 `charged-work-implementation.json`，原static23-row draft与原freeze均保留。实现把新entry/返回predicate、紧缩邻接header初始化、初始/layer move、path parent更新、reverse、返回pending复制逐项收费。故最初未冻结的79/111/177草稿值被补齐成最终**80/112/180**，发生在任何candidate执行之前。最小手算：旧greedy40 +entry1+setup39=80；第0层57到137，第1层30到167；检查/重建11到178，caller predicate2到180。首个child状态/路径完整建好在112，尚不代表完整可行cut。179预算会在最终status付款前拒绝完整local order，180才返回有效。原始每操作transcript保存在 `literal-charge-gold.json`；large-mask控制存费用histogram以降低共享低RAM宿主读取成本。

未来编译/执行计划是GCC15.2 O2 gold与same12 driver、Clang21.1 O1 UBSan gold、以及GCC standalone submission TU编译；进程专用TEMP/TMP/TMPDIR均设本项目F盘目录。F至少1GiB空闲才执行，当前仅做read-only剩余空间观察；绝不清理用户文件或改系统环境。所有stdout/stderr/actualexit与编译输入SHA要保留。时间只记共享功能cost，不做性能比较。

父任务先审 `pre-execution-freeze.json`，此阶段不运行任何上述编译/执行命令。后续范围仅160及R52同12；63/67/250/1099/性能/默认推广仍未授权。
