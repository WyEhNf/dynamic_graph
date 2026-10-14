# 纯树物理年龄候选

Sethi–Ullman 需求是放松寄存器机容量界，不能确定 distance ISA COPY 数。
R144 仅读取冻结全336/72原输入与实际输出，归因每个 COPY 携带的原身份；
没有用易族替换分布。当前默认和 R109 质量继续冻结。

新 matcher 支持完整、无共享 ADD/MULW 输出森林、重复有序参数（同一子树
只发一次）、未用 GET；原 GET/SET 的寄存器必须各唯一且读写集合不交叉，
无 order_deps。共享/hazard/原 COPY/dead arithmetic/深度超限明确拒绝候选，
不表示整个输入无解。未用 GET 最后发射且保留全部原节点。

对每个子树和外部必须持续保留值的**有序 latest-age 向量**缓存资源方案；
枚举两种 DFS 子树次序，先计算第一子树，再以它的真实结果年龄加入外部
向量计算另一子树，最后原算术消费两身份。不同身份/参数角色不折叠，
相同 shape 缓存中仅恢复相对子树角色；最终逐原 ID 发射，原有序 args 原样映射。
只有年龄完全相同的出口状态可合并为最低 COPY 成本，不使用未经证明的
分量年龄支配关系。max_outcomes 截断记录而非最优性证明。

每次即将发射原指令时，若最老 future-needed 身份年龄 W 且此次不消费它，
先 COPY 它；新物理槽推进其他年龄，直到可以发射。SET 无临时结果仍推进
槽，重复参数消费去重但发射参数保留。这个 deadline-only timing 是固定
候选构造，不称固定顺序 COPY 最优（现有 fixed_order exact 允许提前 COPY）。
至多 W 轮旋转仍不能前进则受限失败。总预算从 matcher 前开始，覆盖 memo、
恢复与 emitter；state/time 预算耗尽均 unknown，不返回未经完整恢复的输出。

预声明验证：小新树允许任意 ready 排列与提前 COPY 的独立 raw-age oracle，
比较可行性和 COPY 差距（允许新候选劣于全局最优）；另穷举所有 DFS 原
次序加独立 deadline relay 来检验 memo 对自身候选族的最小成本，若发生
outcome 截断则不给 exact DFS 最优结论。包含所有四宽度、左右 args/真实
拓扑/opaqueID、duplicate/unused GET、SET/hazard/shared/COPY拒绝与预算unknown。
持出树将改变形状、padding、多个输出，保留已合法旧输出作为 incumbent。
