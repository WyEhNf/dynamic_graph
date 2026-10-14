# R150 原因驱动的 single change

实际旧64/W4 padded24 COPY vs DFS37，旧256/W8 padded56 vs DFS67；两个
实际旧原次序均非子树连续DFS，所有COPY均距离W，并无提前COPY。
R150保留两个完整原inputs、before/DFS outputs、originalorders及COPY traces。
完整双链10节点W4例，GET+3 unary自引用链各一条：两种整子树DFS都1COPY，
交替原次序0COPY。仅该双等长链族最小2W+2，非所有DAG最小。

新显式tree_pipeline.py只加一种局部调度：一个二输入原算术的两个独立
子树均严格GET起始、内部只有ADD/MULW重复引用直接前驱时，枚举两链的
逐原interleavings。其他原树节点沿DFS两方向；所有外部身份在此子树内
持续future-needed，不消费，不折叠。matcher唯一disjoint regs、无hazard、
无共享、保留未用GET与所有原算术；原COPY/dead arithmetic等不支持。

状态 (prefixA,prefixB,external ages,已出生A/B latest ages) 记录完整角色。
发射链A或B下一原，自己的上一个身份被消费，deadline COPY所有其他
live；出口年龄按external/A/B角色恢复，各实际原ID只由其链prefix确定。
最终共同父算术有序args不交换，按原身份再次emit，不用数值相等关系。
等状态留最低cost；不做年龄支配、不新增GET/重算/删除。局部lattice完全
排空才称这两条链deadline timing族最优，任何global outcome截断均记录。
20k全局state与500ms总deadline从matcher前开始，覆盖恢复/emitter；超限
unknown且旧已验证incumbent始终在独立driver保留。默认auto不动。

预声明gold：10节点完整0COPY例，长度1..5双链/混合ADD-MUL有序左右args，
每宽度4/8/16/32，所有二项interleavings独立raw materialize取min；局部
外部age组合须持续保留，不内部consume/hazard，并回传每身份age。再已
有120输入raw任意ready/earlyCOPY oracle+新family局部穷举对照，保留68旧
exact/52unknown（不因候选变化改旧oracle状态），新增独立检查全部输出。
若通过，旧48+新36 same500ms/20k固定incumbent一轮，全部12/7旧proof
保留，任何unknown不变proof，不扩大整个336或把局部胜利称官方Level。

静态源码与gold先冻结，19窗口未明确释放前不运行测试/求解/编译。
