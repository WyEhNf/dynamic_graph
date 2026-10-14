# R193：移动节点与固定长序列的隔离实现（只冻源，尚未功能执行）

前置证据：R192独立保存输出审计，272份原身份/有序引用/物理距离/RAW-WAR-WAW通过，R189全部top8身份及21族归属逐项一致，总COPY192859；手工45的58→45物理行（13→0 COPY）通过独立符号与9整数初值模型；944个连续<=32区域逐项证书最小GET→固定MUL距离12>W4。首个R191审计器错误把外部id当数组位置，原失败及旧源237ea74…保留；R192按数组位置解析，不能把此修正算算法收益。

## 唯一机制、身份与时钟

新增三个隔离模块/脚本：`mobile_backbone_anytime.py`、`mobile_backbone_refine.py`及独立`raw_mobile_backbone_reference.py`；不改default、R183旧core或selector。生产解析/物理COPY `_prepare/_prefix/_step`复用冻结R183源263e3e…；旧prefix严格读取initial真实physical rows，包含原SET无输出的槽及首次regional original前所有COPY，绝不按原rank假设0年龄。

每邻域固定L/R与<=32原数组位置ID mobile。其它跨度内原指令保持initial相对序成为backbone；prefix所有physicalrows完全保留，suffix仅原节点相对顺序固定，按candidate真实角色重新emit COPY。所有动作保留原opcode/reg/有序操作数、每original一次。角色覆盖所有未消费DATA身份，包括未来mobile、backbone和整个suffix；内存hazards只限制ready，不作为temp生存。

完整state为`(mask, backbone_cursor, sorted(real identity, latest physical age))`，completed由physicalprefix、mask与cursor前全部backbone决定。相同mask但不同cursor/不同任何身份年龄不能合并。动作是任意ready mobile及下一ready backbone，至多33，COPY仍最新/到期（含W年龄非last operand须接力），无earlyCOPY、别名、重读GET、spill、重算或重结合。`g`完整已发original+COPY行，`h=N-L-popcount(mask)-cursor`含固定suffix所有尚未发原操作；只有unweighted g+h剪枝是安全必要界，w2仅排序，无COPY近似保证。

budget仍每input500ms、累计20k expansion与20k真实transitionattempt、最多64邻域/每邻域16完整出口；parse/initial验证/selector/prefix/每action真实模拟/恢复suffix/真实complete gzip写均计search clock。cap继续下一邻域；时间、expansion、attempt、resource停止全输入，partial与完整候选全部保留。现模型准备扫描/字典复制是合作式时钟检查，500ms是搜索截止，不能宣称系统调用/单次parse/I/O的硬实时端到端保证。producer全部search停止后独立export JSONL和raw replay，其时间另列，绝不补旧时钟。

selector按R190已审input-only闭包：实际被COPY的真实身份u；<=31 directusers含u/全部users，>31仅含最晚user并使u保持external；private唯一consumer祖先及唯一后继闭包，>32全anchor拒绝，不截掉原节点。共享GET所有datausers不在mobile则拒绝；L在minimum mobile前的最后外部data/hazard前驱之后，R覆盖mobile及所有外部直接datausers。复制次数/最大间隔/original数组位置排序、去重、64cap。当前shared/root持续存活可能接近物理必要界，不声称跨跨度就能省cross1024的1033差额。

## 原始物理参照、全部出口与独立验证

独立N<=9参照不用生产parser/ages/_step/状态或selector。原始有序refs、pairwise同寄存器RAW/WAR/WAW、W个真实physicalslots，Dijkstra COPY成本1/原发射0。移动原可任意ready、backbone/suffix逐序；COPY允许任意旧/最新副本、early/deadidentity，因此比生产COPY族广。只有完整队列穷尽/首个minimumcost完整goal才分别为**此邻域**闭合阴性/最优；预算/发现数量/attempt/time皆unknown。原80都有已保存合法initial，不能假装会产生真阴性；阴性控制为格式/非法有序身份/SET来源/COPY unsupported拒绝，而不是图无解。N>9（hand45/matrix160/fanout81）明确not_applicable，不拿tiny optimal当一般DAG全局最优。

独立`MobilePhysicalReplay`从raw真实prefix与immutable predecessor逐物理ring推进，读取cursor确定真实done，所有未来DATA角色/真实最新副本年龄、g/h每record对照；不调用生产transition。labels每version保存独立ring，OPEN/unfinished引用不可变版本。真实输出全部四验：raw identity+有序args+hazard/window、生产符号verify、另一个独立opaque有序符号解释器，以及8signed/16unsigned/32signed两个异初值整数重放。本地整数语义不是官方位宽。

## 预声明唯一小控制（当前未授权执行）

`research_mobile_backbone_small.py --prepare`只复制源/旧输入/旧initial/gold、构造字面固定串行fixture、AST解析/资源JSON原型，无solver/reference/oracle/test执行。将原80 frozen小图按all-mobile L0/RN-1执行新单邻域；读取已冻67exact+13unknown，不重跑旧oracle/baseline。新reference仍20k states/discovery/attempts与500ms，所有新unknown保留，不要求匹配旧unknown证明。另固定hand45实际selector、matrix160/W32 SHA06f7a8…的R187 initial C64、GET/SET hazard6/W4、一个共享GET40 distinct消费者的81条原输入，合计84（与旧树84不是同集合）。所有completed proposal包括更差与非胜保留，保存baseline/best/全labels/OPEN/unfinished；hand45是否找到0只报实际，不预设。

预声明15项合同：长跨度closure；真实非零prefix的COPY+SET槽/固定suffixexternalrole；cursor前全部done/重复原拒绝；RAW/WAR/WAW屏障；>32fanout根external；W边界非last接力；总deadlineunknown保留initial；preparedforeign；mobile重复/越界；N>9参照拒绝；unknown opcode/原COPY拒绝；reference极小budgetunknown；真实UTF8长reg proposal包络；完整sink后中断保留goal；第一16 cap后第二邻域继续同initial。最后合同使用17次实际synthetic callbacks（前16为同一完整baseline、后1手工完整见证），明确是dispatch测试，非17个新搜索解。

不执行full336/不promotion；原272合法+47 scopedproof/9budget/8failure、全部21族/原分母保留。新小控制84若成功只支持该机制功能与局部收益，不支持官方Level1/3。R143 legal272必要均值10.285229311249013%仍只严格identity、自生成分布、等权output分母；官方Level2和平均/分母未核实。

## G资源上界与终止合同

大型产物新owned `G:\Hackathon-stage2-artifacts\project18\r194-mobile-backbone-small`，准备时必须不存在，执行时CreateNew目录；输入/源码/小report留F，不junction、不移删旧文件。实际resource_snapshot读取G剩余、Fsmall剩余、RSS/进程生命周期峰值/实际freeRAM，producer G>=512MiB+当前input package、Fsmall>=64MiB、RAM>=768MiB才运行。每complete先完整写/flush再检查资源，resourceStop保存该actual wholeproposal与partial/fallback。

沿用真实UTF8 opcode/reg/ordered arity/block_id长度计算，不假设官方identifier长度。proposal行数<=initial实际F+N*W（保留任意多初始prefixCOPY）；所有原GET/SET长reg仅对应原行出现一次，COPY无reg。新增cursor数字<=N，计算label/open JSON prototype分别需<=1KiB/2KiB，actual每条检查，header<=4KiB；20064 labels+OPEN（相同输入所有邻域合计charged20k transitions+64seeds），诊断上界约61.5MiB。以真实小84 inventory生成每input package与global1024proposal无压缩上界；gzip无损流式、不给压缩率保证，之前R186整336上界175973778432B也不能当本小批实测。

既有R187实际全部输出gzip27,425,437B、diag gzip16,256,277B、OS processpeak90,742,784B仅旧机制证据，新cursor/大跨度未运行，不能称新峰值。没有资源benchmark或吞吐测量。预算未完成/资源停tail按原84记录resource_unknown，旧initial继续保留。OSError写failure不自动重启/换名字；所有文件压缩/decodedSHA与source freeze索引保存。每pair诊断独立export后release，禁止跨输入累积原始前沿。
