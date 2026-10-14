# 矩阵共享归约的rook图minor必要容量界

已读一手原文：Daniel J. Harvey, David R. Wood, *Treewidth of the Line Graph of Complete and Complete Multipartite Graphs*, arXiv1210.8205v2，Theorem3。代k=2,c=d，两种d奇偶表达式均为tw(L(Kd,d))=d(d+1)/2−1。作者HTML https://arxiv.org/html/1210.8205 ，PDF https://arxiv.org/pdf/1210.8205 。这里不使用spill、I/O或重计算下界。

若某严格原身份/COPY-only调度合法，删去COPY后得到原拓扑顺序。对每条原指令t取bag=其发射前的未来数据必需身份集合∪{t}。每个原节点在自己的bag出现，直至其最后数据消费者期间连续出现；每条原数据边u→v在v的bag覆盖。合法窗口允许≤W个互异未来必需身份，所以bag大小≤W+1，原**数据边**形成的无向图的pathwidth≤W，从而treewidth≤W。寄存器RAW/WAR/WAW仅约束原拓扑就绪，不加入minor边；COPY不改变原身份数据边。

实际矩阵Ci,j的私有MUL/ADD/SET子图连通且与其他输出私有子图不相交。把每个A行输入组中的第j个GET以及每个B列输入组中的第i个GET归入Ci,j。这些GET分别分配一次，而且在对应Ci,j内有真实数据边，故新branch set仍连通且不相交。同行的两个branch sets由其中分配的A GET与另一Ci,j私有算术的真实边相连；同列由B GET相连。收缩各branch sets得到完整d×d rook图Kd□Kd=L(Kd,d)（extra边可保留）。因此原数据图treewidth≥d(d+1)/2−1。界>W时说明声明模型不可行；界≤W没有可行性结论。

实现不看family名、寄存器字符串里的矩阵坐标或生成seed。先反向计算每个原非GET节点的SET owner，要求私有非GET子图只归一个SET，根GET可共享。把GET按照它涉及的输出集合分组，识别两个各含d个、不相交覆盖全部d²输出的行/列分组，所有交叉有唯一输出，每组至少d个GET。分配branch sets后独立checker从原JSON数据边重新验证所有成员不相交、内部连通、所有d²(d−1)个rook必要边真实存在，并重新代入公式。识别不匹配不是无解证明。

源码只用于离线诊断，默认auto及age_portfolio不修改。严格身份模型外的值别名、额外GET、重算、spill不受此证书约束；源码/证据必须保存供独立复核。d4/d7/d12的理论界分别9/27/77；实际命中数需运行后记录，不能根据family标签直接拒绝。
