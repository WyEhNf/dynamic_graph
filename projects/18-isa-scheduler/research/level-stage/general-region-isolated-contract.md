# R182：独立实现、原始 oracle 与资源合同（只冻结，尚未执行）

本轮根授权仅实现与预声明冻结，**不运行 solver/oracle/unittest/gold**。R180/R181及旧证据不修改；当前普通CLI、auto/default、树策略无新入口。实现是 `general_region_anytime.py` / `general_region_refine.py` 的显式研究API。

## 输入、边界与正确性作用域

COPY-free GET/SET/ADD/MULW；bits2..5；N<=16384是研究容量上限，并非官方最大规模。未知字段/opcode、原COPY、引用SET无结果、错误initial identity/permutation、prepared来自不同原输入/initial均拒绝。拒绝不产生不可行证书。

initial必须是完整真实合法输出，先独立原JSON identity/order replay；本轮未来所有完整proposal还必须分别通过symbolic和8signed/16unsigned/32signed本地整数解释器，不能以identity替代数值规则。局部状态role仅计未来原数据消费者，hazard只控制ready，SET不产生身份，dead GET/死算术仍发射占槽。年龄到W且尚有后续消费者的操作数须COPY，当前读不能刷新原值；只有本条最后消费才能直接覆盖。

prefix切点在第一条区域**原指令**之前，包含它之前所有initial COPY；prefix逐物理行原样。真实prefix外部身份中，区域及suffix任一未发directconsumer都保留。region完整后逐原恢复initial固定suffix；只有整块恢复、原排列和N+COPY及endpoint一致后，才能送complete sink。受限suffix无法恢复返回partial而不是unsat；不会提交半个block。

精确state是32bit done_mask与所有真实identity/latest-age，low-g才replace、immutable predecessor version、reopen、stale rejection。只在这种限制COPY策略的相同完整状态合并，不做scalar年龄等价/shape对称/值别名。weight2仅排列，g+h完整原行必要界剪枝；不称COPY近似或全图最优。

## 总预算、尚未发布邻居与出口

每输入总500ms/累计20k expansions/累计20k实际transition attempts，32region/64regions/每region16完整出口。sameinitial、不组合gain。first region cap只停自身，若总budget尚有空间继续下一region；整体partial和cap列表保留。时间包含parse/identity预检查/selection/prefix、ready扫描、每条动作真实模拟、恢复suffix和sink JSON/I/O；producer导出诊断/四验证单列。正预算不能保证500ms硬实时，因为一次parse等不可抢占段和OS时钟。

每个ready先计attempt，再模拟恰一次；邻居按预计COPY/liveΔ/GET剩余consumer/initialrank固定排序。prepare中断时已模拟但未发布buffer不算labels/OPEN/完成候选，可以丢弃，保留parent完整state、phase、cursor及buffer数量；publish中断保留已发布labels与剩余cursor。只全ready发布后标完整expanded。goal suffix中断为未完成goal，先前完整best保留；goal sink已保存后的resource中断须保留该完整候选和真实partial。诊断引用O(1)交接，所有label/OPEN流式后导出并按input释放。

## 独立 broad raw oracle

`scripts/raw_general_region_oracle.py`不导入任何isa_scheduler模块。直接重建原t#数据边与同寄存器RAW/WAR/WAW；state=(original completed mask,物理最后W槽全部身份历史)，同身份旧副本可重复占槽。Dijkstra原emit成本0/COPY成本1，允许**任意时刻COPY任一旧/新代表，包括dead身份**。原emit可选择旧来源；这些来源不影响后续physical history，恢复一个最新来源的等价见证，COPY动作仍逐旧位置全枚举。SET槽记None，绝不COPY它。

N<=9，预声明80固定新seed，分别W4/8/16/32，带shared arithmetic/重复输入/随机GET SET同reg。固定max expansions20k / max discovered20k / 500ms；discovered cap是内存保护，独立记录unknown，不能伪闭合阴性。首个Dijkstra goal弹出则严格模型最少COPY；仅完整OPEN耗尽是closed infeasible；budget/discovery/time全部unknown。它允许early/old COPY，候选更差是允许的，不能为了对齐把oracle降成生产transition镜像。

后续运行需新授权：80所有正/阴/unknown原样保存；candidate任何合法C不得小于已证明oracleC；candidate无解不要求oracle阴性。手工11全witness虽已由root独立验证3→1，当前新search尚未运行。首次实际runner还须对每个完成proposal独立raw replay+symbolic+三整数，而不只best。

## 十个封闭合同测试（已写，未运行）

1. exact low-g reopen/stale与旧label不可变。
2. oldest年龄W、当前operand非last时先COPY。
3. 首region原指令前initialCOPY精确保留。
4. prepared input不匹配/unknown opcode/N过界拒绝。
5. transition cap在prepare中途，buffer未发布，只有seed label。
6. 第一region出口cap继续第二，后续budget仍保留初始best（mock dispatch，不能当真实搜索质量）。
7. 序列化label/open上界以及很长寄存器名的完整proposal估计。
8. SET→GET hazard、unusedGET和suffix数据role，SET无结果。
9. sink实际接收完整goal后resource中断，保存candidate/best和真实partial，不补时钟或删出口。
10. actual disk snapshot低于reserve时，在search前返回resource unknown，完整initial fallback保留，不调用child。

独立raw N<=9实例和这些contract fixture冻结后不更换输入或用更简单分布宣称Level。尚无执行通过统计。

## 按真实F/N/W重新推导字节包络

initial可以有冗余COPY，故单独N*W不能覆盖保留prefix。令F=实际initial物理行数，任意proposal preserve prefix≤F，余下每原最多W行（W−1 relay+1原），**完整行数≤F+N*W**。该上界覆盖SET/unusedGET占槽；受限旋转W失败不产生完整proposal。

`resource_layout`按实际输入的block_id/reg JSON UTF-8大小、最大id/距离数字长度核整份完整original行，再加最大COPY行和original_order。长寄存器/长block ID不能复用固定17MiB。标签与OPEN取真实N/W/F的最坏数值，用实际json.dumps(serialization)字节数检查<=1KiB/2KiB；>上限显式unsupported+initial fallback，而非悄悄截断证据。规划20064labels×(1+2)KiB+64×4KiB=约59MiB诊断，仅规划磁盘量不是已测RSS。

最多1024份完整proposal累计可能**数十GiB**，绝不假设512MiB能容纳所有。future producer必须流式写每份complete，以当前disk free检查至少512MiB reserve；前置检查本input两份proposal包络+diagnostic+64MiB slack若超reserve则resource_unknown，不启动该input搜索。每次sink保存实际complete后如达到reserve，抛RegionStop('producer_resource_reserve_after_saved_complete')，原best/partial诊断保留，不再尝试下一region；不可把沉默丢输出称completed。F为实际基座，不由ca93单例猜硬上界。producer自身OSError终止保留原件，无自动重启。

目前仅freeze脚本调用纯序列化layout（hand11以及N16384/W32/F16384规划例）；**没有实际求解或资源RSS测量**。未来runner须实际记录before/after磁盘free、诊断bytes、所有输出bytes、peak process/RSS、search/emit/export/JSONI/O/四验证/end-to-end和unknown数量；没有runner执行权限，因此本轮不创建伪性能报告。

R183静态补充：wrapper已经实现实际disk snapshot（默认项目盘shutil.disk_usage；测试可注入），preflight必须free>=512MiB+本input诊断/两proposal/slack且package<=512MiB，才启动搜索。每个实际complete在producer callback写后立即再读free；跌破512MiB通过RegionStop闭合保留已保存proposal/best/unfinished，停止该input，返回partial。OSError不伪装completed。资源snapshot及stage记录于stats，仍全部计search时间。这只读磁盘信息，不关闭用户应用，不产生资源负载。
