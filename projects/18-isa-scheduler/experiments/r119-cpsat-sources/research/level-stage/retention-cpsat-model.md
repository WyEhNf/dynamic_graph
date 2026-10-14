# 可选CP-SAT原位置/活跃区间模型

独立于默认调度器，OR-Tools可选独立环境。前提是已经由raw物理年龄oracle核验的retention-order桥梁，原GET/SET/ADD/MULW各一次，无原COPY/额外GET/重算/别名/spill。这里只求合法顺序，不求最少COPY。

N个原指令position是0..N−1的全排列，所有原data和RAW/WAR/WAW依赖均约束前驱position小于消费者。原数据身份v有未来消费者时，设置last_use=max(所有原data消费者的position)，用整数区间[position(v),last_use(v))、单位需求参与Cumulative(W)。整数时间t对应原指令t发射**之后**的前沿：v刚产生即计数；最后消费它的指令发射后不再计数。不能改成闭区间或把ordering deps当data use。

无未来数据使用的原节点（SET、unused GET或死算术）仍在[position,position+1)贡献单位需求。若它发射前满W身份而没有最后消费，发射后仍W活跃，再加这条死物理输出槽会超过W，所以模型拒绝。若最后消费至少一个，则after-live≤W−1，死槽合法。有未来使用的原节点在区间起点本身已计新身份，如果满窗无最后消费，after-live会为W+1，同样被容量拒绝。由此该Cumulative条件等价桥梁两个条件，覆盖SET没有未来结果却推进窗口的情况。

先祖/后代原节点数量仅缩小position合法domain，不删除合法顺序；数据参数仍由真实原JSON映射，算术有序args不能被重算、交换或改写。solver只给顺序，实际物理COPY由发射器产生，保存输出还须独立原JSON身份、符号和三整数配置重放。

模型中没有generator-specific对称约束。单worker、固定seed、有限搜索预算，模型构建/求解分别计时；搜索预算不是包括依赖导入、输出、完整验证的硬墙时承诺。UNKNOWN只是未知；MODEL_INVALID报错；只有backend INFEASIBLE才记录“求解器在声明模型证明不可行”，这不是可独立逐边重放的便携证书，也不等于官方允许重写的整个问题不可行。导出实际.pbtxt模型和输入hash，不能根据一次timeout改成proof。

直接相关工作：Chen的min-reg DAG调度CP-SAT方向（https://arxiv.org/abs/2303.06855v4）；这里增加窗口满载死输出条件，不借用论文最优性。OR-Tools官方Python安装说明 https://developers.google.com/optimization/install/python 和API https://or-tools.github.io/docs/pdoc/ortools/sat/python/cp_model.html 。安装于.venv-cpsat，不改变既有标准库.venv。
