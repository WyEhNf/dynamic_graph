# VM 第三阶段静态方案：独立 threaded dispatch

本文件只作静态方案，没有实现、编译或测试新代码。第二阶段3230的TOS2在60/60配对中变慢，完整负证据已冻结，第三阶段不叠加该cache。第一阶段bf54以及普通4f73继续保留。

## 选择与待核瓶颈

先选GNU computed-goto分派，保持第一阶段decoded operands和原vector栈。它只把每个opcode的handler尾部连接到下个opcode，不同时改栈、融合指令、缓存M、减少原步骤、改变数学认证或AUTO。拟新后端 `decoded-threaded`，CMake独立默认OFF。非支持编译器使用原decoded-switch fallback并在指标说明实际分派方式。

当前已观测的是33opcode源码switch、阶段1typed-decode的正负数据，以及阶段2nm中独立pop lambda clone符号；尚未核当前decoded机器码switch实际是否为jump table、是否已经预测良好、IP链/分派/stack分别占多少。不能把33个case解释为33次条件判断，也不能把TOS2失败直接归因于spill。待27窗口结束后，先只对冻结bf54/3230解读既有机器码，记录dispatch间接分支位置、pop/helper调用和PC更新；仍不启动新编译。

目的是假设不同handler尾部的分派位置能改善预测/控制依赖，实际仍可能没有收益。若GCC将尾部合并为同一间接跳转，源代码computed-goto不能冒称实现了多dispatch site；新编译后的反汇编必须核实，合并结果作为可复核观测而保留，不根据某源的时间改flags求好成绩。

## Primary核验

2026-10-11重读[GCC官方Labels as Values](https://gcc.gnu.org/onlinedocs/gcc/Labels-as-Values.html)：label必须属于本函数，跳表访问不自动检查范围；inlining/cloning会影响label地址稳定；GNU C++跳出对象作用域不会像通常作用域退出一样调用析构。因此label地址仅由当前函数内部生成和使用，所有函数级资源在首个间接跳转前构造，handler局部只允许POD或先正常退出block再dispatch。静态label table配合稳定非inline函数；GCC可用noclone，Clang按支持的attribute/静态label规则处理，不能盲用未知attribute。

[Lua5.4.9 ljumptab实际实现](https://www.lua.org/source/5.4/ljumptab.h.html)展示handler尾部fetch后跳到下一handler的编译器条件模式。本项目只借此架构说明，不复用其源码，不引入Lua依赖，也不套其数值/异常契约。

[Ertl/Gregg2003](https://jilp.org/vol5/v5paper12.pdf)讨论indirect branch与解释器结构，但旧硬件与模拟数据不能预测当前Zen4；[Ertl/Paysan2024](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2024.14)的原26页PDF指出轻量loop VM可能受IP更新依赖链限制，改dispatch并未自动减少PC更新。本阶段仍保持每原opcode的PC更新，若它主导就可能负。[Cacao原论文](https://www.complang.tuwien.ac.at/cd/papers/A73-full.pdf)说明superinstruction的异常/控制流边界问题，当前不复制机器码或融合块。

论文引用的2015 Don't trust folklore链接受到HAL访问保护，本次未读其正文，不据标题导出本机性能结论。

## 语义设计

1. 单独stable函数负责threaded执行，函数级decoded plan、output、slots/initialized、原vector栈、steps/last-PC与最终计数RAII在任何dispatch前构造。存储仅属于一次execution，解码计入compute/prepare，原Metadata/完整图/PROGRAM保持。
2. 新handler全部33opcode逐条独立，FP64pop/计算/写回顺序与旧handler相同；不隐式FMA、不重结合、不删TRUNC/initializer/unused参数。错误信息/状态/触发原PC保持。
3. handler block正常结束后再执行NEXT：先按原位置检测stack>4096，然后检查pc是否结束，再记录last-PC、`++steps > limit`，取一个原instruction并增加pc，最后跳入handler。RETURN直接return，不额外执行NEXT；program end仍按原错误。
4. 33入口jump table只用编译期enum映射。索引范围显式检查，负或999等非法enum跳到INVALID handler。INVALID仍先按原default路径pop right再pop left，再报invalid opcode：不足两个值应先报underflow，不能把错误提前到decode或表索引检查。
5. immediate无效标志延迟到原handler触发。JZ/JNZ先pop条件，仅采用分支才验证目标；STORE先查槽再pop；WRITE先pop value、再pop/index-check，最后finite-check；RETURN先pop/status再栈平衡。这些顺序不能由prepare改变。
6. label address不写Metadata或可跨函数复用的plan，不从外部数据读取，也不复制到其他函数。GNU-extension编译探测与portable fallback隔离；基础编译flags保持，无全局march、fast-math或FMA许可变化。

应避免为减少代码重复而重构当前已冻存switch/default：新TU可以复制必要的检查/原handler语义，采用共享审计清单和差分测试防漂移。若需要新共享header，应只供新后端使用，既有数学runtime和旧handler先不移动。

## 必需证据与阶段门槛

实施前：保存本方案和primary来源；读取冻结机器码以核实际dispatch形态。实施时：独立build/源/EXE与严格flags冻结，原switch/newthreaded同二进制、bf54独立功能baseline；GNU路径和强制fallback各独立验证。

功能先验证404原合同与480深栈/异常/步骤集，全33入口及非法enum空栈/1值/2值/未到达场景，jump进入任一opcode及end边界，预算0/恰到RETURN/差1，重复execution不泄露cache。另验证RAII：正常return和throw释放函数级资源，跨handler不带非平凡局部对象，并用可用sanitizer/静态审阅检查；不得仅以一次编译成功代替C++作用域合同。

然后全12实际VM C/全部FP家族与新源/shapeholdout，原C完整文件及source/input/oracle/Metadata/SHA冻存；newdefault保持legacy。fallback要输出真实effective dispatch，不能把switch-fallback称GNU实测。原N10000copy仅显式budget的旧资源证据，不重复冒称默认已过。

功能验收之后再冻结有限同binary decoded-switch/threaded五对计划、每原steps/错误契约相同，全部case保留；解码/compute/IO/wall、外部校验与宿主负载分开。性能需根新窗口，本阶段现在没有CPU批。结果负则保留不晋升，不临时叠加TOS2或fusion求正。

## 暂留的另一方向

若以后选择小块fusion，应作为第四个独立阶段。理论上LOAD/LOAD/BINARY/STORE可以减少分派并保留每条原step/error检查，且从任意原jump入口仍须正确执行；不能简单把四条算一步或先验证坏第二槽。每条中间栈效果、overflow时机、uninit检查、FP顺序和steps-budget中断都需保留。它能实际减少分派次数但更易产生语义漂移，因此本次先验证单一threaded机制，不同时做fusion。
