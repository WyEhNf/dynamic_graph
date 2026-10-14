# R56 静态收费勘误与拓扑对应（未运行 reference/compiler/solver）

首版 `literal-hand-trace.json` 手算漏了未完成目标 J2 的 `target_visit=1`。源、独立 Python reference 和收费契约都已经计入此项；错误仅在手写累计表。本轮不修改它和原 `source-before-gold-freeze.json`，保留首版错误证据。新增逐项手工64行表 `literal-hand-trace-revision1.json`（每行操作、费用、累计费用），首个暂存pair为75，完整扫描为127；旧74/126不能再作为正确金标。预算边界相应为0/3/4/74/75/126/127/128。

若下一次获准运行独立 reference，生成的 literal-charge-gold 应自然得到75/127；应在产物中明确这是预执行静态修订的结果，不归因于候选输出。不得覆盖旧手写表或重写旧freeze，也不改C++费以迎合原手算。

## R51 Graph::Graph 与 reference context FIFO 一一对应

* `research/batch51/solution.cpp` 的 Graph 构造器先按原 `nodes` 记录顺序分配index。对每个节点按原 `inputs` 记录顺序，执行 `in[i].push_back(p);out[p].push_back(i);++degree[i]`。reference `context(ns)` 同样以nodes列表顺序建Python插入有序dict，再按该nodes顺序及每个inputs列表顺序 append 原ID到out。
* 原 C++ 先从index0到n-1将degree0节点加入topo，再依序访问可增长的topo vector。reference先按dict插入顺序收集degree0节点，然后 `for i in topo` 访问可增长的Python list。两者均按out的构建顺序递减degree，首次归零即append，都是 FIFO/记录顺序，而不是按ID优先队列排序。
* Reference使用原ID、C++使用index；映射是Graph的原record-order ID↔index双射。fixture的稀疏ID变换、nodes倒序和inputs倒序会同时反映在双方的构建顺序中。没有在reference中另行按ID排序topo或输入边。
* held top24的排序单独按(-output,原ID)构造，与原outer比较器一致；它不是topo的排序规则。向量done/users的物理定义依照原DIRECT边。
* 对4节点首例，输入记录P0,Q1,J2,C3，roots为P,Q。出边P→C（Cdegree2先减1），Q→J（J首次归零append），随后J→C（C归零append），双方topo均P,Q,J,C。DFS用LIFO栈：C的inputs按P,J压入后先弹J再弹Q，最后弹P，与逐费表一致。
* 已执行 `external-release-static.json` 使用的ID有序heap仅用于拓扑无关的可达/强制界静态归因；不用于literalfee reference。其可达集合/去重持有界不依赖合法topological order的表示，不需要把那份历史报告偷偷改成FIFO。

当前source仍3a4f184de2759fdcd1cbfd899c5f8029e2f7f2691743ec214a895123db19c21a；reference generator仍495c6d82a877dd111163f2f636ffac657802e08879041791262d65669414f800，均未执行。默认R51、用户旧打开Tex不变。
