# R190：单一下一机制——移动生产/消费小集合与固定backbone交错

**当前只计划/静态手工见证，不实现、不solver、不改default/已冻源码/旧证据。** R187由root独立actual42aa60全5116输出/全部711769 labels及OPEN/unfinished通过；下一阶段保持原336/21族272合法+47/9/8原状态。

## R189只读归因与必要界口径

R189读取R187实际best/所有4680候选，逐COPY追原identity，并接R143同输入SHA必要界；无调度器/验证器/oracle import。164真实搜索=53 transition预算、90时间、8cap、13完成；4680完整proposal中98低于initial、2893同值、1689更差，不能用23最终改善替代全搜索状态。近窗口链C135089/L134208、ladder8334/8330几乎没有可证明的大余量，不继续按绝对COPY最高排名。

实际/必要下界：cross9750/7956（gap1794，潜在272等权COPY/output改善上界0.3671pp）；sparse_shared4992/4028（964，0.1866pp）；matrix66/0（66，0.1333pp）；dot2876/1677（1199，0.3099pp）；padded3885/0（0.5884pp）、ragged4036/0（0.5625pp）。L0或差值大不证明能零COPY。272固定合法子集必要均值仍**10.285229311249013%**，全336必要条件仍11.986950679066013%；严格identity、自生成分布、等权output分母，**不能称官方Level失败/通过**，64输入无合法结果使全input真实质量mean仍null。

cross1024/W8的5 GET仍1573COPY，出生→首consumer只1–2原条；cross4096/W16多数1–2，sparse4096/W8为1–3。故“再晚出生GET”并非这里主要机会；长persistent-root稳态COPY可能接近真正物理极限，当前较松necessary gap不应许诺可省1033。matrix160/W32尚64COPY，其中41来自ADD、8MUL、15GET；8份高复制ADD只有一个directconsumer，却等待40–59原条。dot4095/W8仍2196，其中1878ADD，单consumer等待16条；现region改变它时159候选全更差。当前连续32且固定suffix限制真正生产/消费配对，扩大时间不改变这个邻域。

## 唯一变化及能改变的决定

替换**连续32原rank区域**为**最多32个mobile真实原节点+跨越较长跨度的固定backbone**。其余原节点保持原initial相对顺序；selected mobile可以在这条backbone任意合法位置交错发射。prefix和suffix仍保持同initial，所有proposal同initial、不组合gain。不是把跨度内所有节点开放或扩大mobile/state预算。

本质新增决定：私有生产链及唯一consumer可以一起穿过40+不相关原指令，而不是只在32窗口内微调；共享GET与其小数量消费者完整组可移动以改变共享身份出生/退休重叠；matrix私有MUL/ADD reduction链可与其consumer共同提早完成或延后生产，跨越其它Cij链，**不假定整个Cij原子最优**、不重排有序args/重结合ADD、不移删原GET。大fanout GET若全部消费者>32，不能假装整组能移动，只选合法consumer私有closure且GET仍boundary，收益未知。

### 固定input-only mobile selector（未来冻结实现前根再审）

固定每个被实际COPY身份u构造一个anchor。若u的distinct directusers为1，seed={u,唯一consumer}；若2..31，seed={u,全部directusers}；若>31，只seed其initial rank最晚的directconsumer，u保持boundary。对seed闭包反复两条规则：逆向纳入仅有一个distinct data consumer的private祖先；向前纳入一个distinct data consumer的后继，直到SET/多消费者边界。集合每步按original ID顺序，closed集合>32则整个anchor记未覆盖，不裁掉任何原操作或冒称全图unsupported。shared GET只有在所有directusers都在seed或最终closure时可以在mobile中；否则其真实身份在外部。这个seed/closure规则不是family-name过滤。

跨度固定：m=min(initial rank of mobile)。在mobile所有原data/hazard前驱中，取不在mobile且rank<m的最大rank p；没有则p=-1。L=p+1（因此L<=m）；其余更晚的外部前驱留在backbone并由ready制约。R取mobile所有原rank及mobile所有外部direct data consumer的最大rank。所有非mobile [L,R]原节点保持initial相对顺序成为backbone，prefix<L/suffix>R固定。这允许移动穿过长间隔而不假设晚backbone前驱已就绪；不能从candidate/gold挑区间。排名COPY(u)降序、u→最晚directuser原rank gap降序、original ID升序，closed mobile/L/R相同去重，最多64。所有未覆盖anchor数量单列，不把未覆盖图过滤出全336口径。

## 精确状态、目标和转移

state=`(mobile_done_mask<=32bit, backbone_cursor, every_real_identity_latest_age)`；completed由固定prefix、mobile mask、cursor前的真实backbone节点决定，RAW/WAR/WAW仍只ready约束。动作是任意ready mobile或**下一条**ready backbone原节点，最多33种；backbone节点受mobile前驱阻塞时须先发真实ready mobile。保持每original一次、所有原有序引用、SET无值/deadGET推进槽。相同完整state才low-g merge/reopen，predecessor不可变；不做scalar-age对称/alias。

COPY仍R183 latest/deadline策略，当前非last operand年龄W也必须接力；不引入earlyCOPY/重算/spill/重GET。g为整块真实已发physicalrows，h为全块尚未发原数量（含backbone/candidate suffix）。fixedw2仅排列，safeunweightedg+h剪枝；不能称COPY乘法近似/全局最优。全部mobile+backbone完成后按initial固定suffix逐原emit，endpoint mask/cursor/roles/g一致且完整N+COPY后才complete sink。

每input仍500ms/累计20k expansions+20k charged real transition attempts、每neighborhood16 complete/最多64。单step邻居排序仍预测实际COPY/live变化/GETconsumer/rank，每动作只模拟一次，prepare/publish/unfinished原样；cap继续下一neighborhood，time/state/trans/resource停止全input。跨度变长可能更容易在首解前耗尽预算，必须保留unknown，不能宣称32mobile就能廉价全局排程。

## 静态完整手工反例（待根独立验证，不作已测收益）

`mobile-backbone-hand45.json`：W4，原GET a用于early ADD→SET out1及late MULW→SET out2，之间40条不同unusedGET（全部原节点仍必须发射）。手工baseline固定顺序45原+13COPY=58物理行；mobile5真实节点[0,1,2,43,44]可整体跨过固定40条deadGET，完整45原0COPY，最大t#3。两个SET寄存器不同，所有源有序/每原一次，不以GET相等alias。任意一个连续32重排不能把早/晚两个消费者与同一GET同时跨过完整40条；固定prefix已有COPY不能删除，固定suffix原序仍需要root，因此零COPY需要这个新的非连续邻域。

这只是完整手工身份见证，还未由本agent实际验证或search。应先根独立四检查并审连续32不能零的边界论证；不能用手工见证说明原cross1024能省1033。另需从已保存matrix160/W32按实际ADD108 birth45→consumer85提炼完整原input/initial/mobile set，不能只剪成脱离真实外部roles的小片段。shared fanout>32/hazard屏障/long-span GETSET可移动范围均须给拒绝或unknown完整实例。

## 文献与适用限界

构思结合已精读[Sugita等CC2023距离ISA作者PDF](https://www.rsg.ci.i.u-tokyo.ac.jp/lab/en/assets/files/cc2023-sugita.pdf)的真实liveness/窗口搬运、[Chen Min-Reg v4](https://arxiv.org/abs/2303.06855v4)的DAG consumer/压力（非COPY保证）、[Hansen–Zhou anytime](https://arxiv.org/abs/1110.2737)的完整incumbent和safe-f/reopen。**该mobile/backbone邻域是本项目提议，不声称论文已有此算法或其最优定理。** 论文spill/recompute不能带入赛题。旧逆向Min-Reg负结果保持，不重复作为默认。

## 后续验收/资源合同（需新授权）

先实现/冻结小独立topological raw histories参照，正/阴/unknown全部保留；mobile全选N<=9时可与R185已有67 exact frozen结果比较（13旧unknown保持，不重跑旧oracle），有hazard/partial backbone/end-before-suffix/GET重读拒绝/firstcap后改善及immutable paths边界。完整hand45才看是否真的找到0；真实matrix/cross/sparse各预声明old inputs，同R187 incumbent、不跑旧baseline，不只扩容易族。

G owned目录大文件无损gzip，512MiB reserve /F64MiB smallreport/RAM768MiB、实际F+NW proposal包络、20064label/OPEN byte上界重新加入cursor字段核算。独立checker从真实prefix+immutable parent推进W物理slots，completed判定包含backbone cursor，所有external future data角色守恒；不能用生产state镜像取代raw induction。所有complete完整四验（原identity/orderedargs/hazard+symbolic+三本地整数），unknown/cap/resource和64原状态/全336分母不变。没有授权再次求解/全336/默认promotion。
