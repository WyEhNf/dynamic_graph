# 四项目环境与资源

2026-10-11实测：Windows11 x64、AMD Ryzen9 8945HX，16核32线程、31.3GiB主机RAM；RTX5070 Laptop GPU约7.96GiB显存；F盘04时前后检查点约40.7GiB可用。四项目已在本机运行，未购买云算力。

| 项目 | 配置的软件环境 | 已用硬件/资源及边界 |
|---|---|---|
| 11 | Python3.13.12基础venv；模型venv继承PyTorch2.12.0.dev20260408+cu128；Transformers4.57.6；Qwen0.5B/1.5B/3B/7B；bitsandbytes0.50.2、accelerate1.15.0；可选Node24.16.0/TypeScript6.0.3 | 3B FP16分块1024：CUDA allocator约6.18GiB、CPU约9.94GiB；7B NF4分块1024：CUDA约6.21GiB、CPU约5.72GiB；四模型磁盘约25.6GB；128K仅分析；TypeScript单个本地npm依赖锁定 |
| 18 | Python3.12.14，标准库，独立venv | 普通CPU；小图10000案例/3策略；大图beam有界，规模及拓扑覆盖继续扩展 |
| 19 | Python3.12.14标准库、C++20、GCC15.2、CMake4.2、Clang21.1；AVX2隔离编译单元及portable回退 | 1/4/8/16线程，普通稠密N10000与M=3，完整800MB输出对原始C oracle逐字节验证；输入与参考大文件保留便于重放，测试期间勿清理 |
| 27 | C++17、GCC15.2、CMake4.2，标准库 | AI Core/显存为题面仿真，不需真实Ascend；研究至10000节点；CLI宿主峰值约405MiB包含JSON/验证器，不是设备显存 |

11两venv分别隔离标准库治理和模型依赖；模型venv继承本机CUDA PyTorch。其余模型依赖在`requirements-model.lock`，不可变模型文件commit/hash在`artifacts/model-lock.json`。Windows原生证书存储保持TLS校验，不配置账号、API密钥或远端模型。

本机工具路径：Python11为`C:/Users/admin/miniconda3/python.exe`；Python18/19为Codex bundled Python；GCC/make为`E:/mingw64/bin`；CMake为`C:/Program Files (x86)/CMake/bin`；Clang为`C:/Program Files/LLVM/bin`。脚本仅修改自身进程PATH，不改系统设置。迁移机器时修改preset/传入Python路径并安装兼容PyTorch。

19普通稠密N10000参考C约504.7秒；默认与内存配置最终均严格通过。单矩阵约0.8GB，普通owned输入复用峰值约2.02→1.22GB，带状仍约1.61GB；它节省RAM但不保证吞吐。参考/输出大文件需单独存储，建议至少4GB测试磁盘，当前长期证据约占更大空间。

11的3B/7B实测均采用连续分块预填充，7B NF4普通约6K输入CUDA reserved峰值约6.60GiB。历史v14完成16380输入/13输出，32700目标阶段人工结束、没有OOM；该失败记录保留。随后v23按层CPU KV卸载加逐预填充分块回收，完整完成32688输入/13输出，单次约54.07秒、CUDA活跃/保留峰值5.91/6.11GiB、独立进程RAM峰值7.87GiB。同一加载模型的v20/v23一对比较完整greedy IDs相同，约256.88/54.24秒，但仅一对固定顺序，不代表稳定吞吐或长工程代码质量。短提示卸载均较慢，常驻缓存仍为默认；128K仅分析，不推理。18/27当前的CPU契约与仿真测试不需专用硬件、虚拟机、CANN或NPU SDK，正式集成另列。

中文TeX报告使用本机TeX Live2025/XeLaTeX编译；Poppler逐页渲染PNG，入口`scripts/verify-research-reports.py`。Qwen0.5B/1.5B/7B为Apache-2.0，3B为Qwen research license，保留原始许可；模型不纳入源码管理。实际模型依赖闭包另存`artifacts/model-environment-inventory.json`，它记录本机安装状态，并非可移植CUDA安装锁；新机须提供兼容PyTorch，再按两份模型/量化依赖文件配置。

软件能力：11需检索、代码依赖、LLM评测及ArkTS集成；18需图搜索/活跃值/语义验证；19需C/LLVM、严格FP64与多核调度；27需离散事件/显存生命周期/异构资源优化。后续资源和工作见各项目开发计划，官方平台配额仍需对齐。

