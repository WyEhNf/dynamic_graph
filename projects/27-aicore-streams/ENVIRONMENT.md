# 环境与资源

本机2026-10-10已配置并实际编译验证：Windows PowerShell，CMake 4.2.0，MinGW GCC/G++ 15.2.0，C++17，MinGW Makefiles。C++提交与评测CLI不使用外部库，不依赖Python、GPU或CANN；测试生成和摘要脚本使用已有Python标准库，无pip依赖。

|资源|开发建议|比赛要求状态|
|---|---|---|
|CPU|4至8个逻辑核心；构建脚本并发4|仅用于生成和模拟方案；评测CPU型号未公开|
|RAM|开发8GB即可；大图批量搜索建议16GB|官方进程内存上限未公开|
|磁盘|预留1GB容纳构建、样例和日志|数据集大小未公开|
|GPU/NPU|无需求|当前题目为离散模拟，无需真实AI Core设备|
|网络|读取官方说明、获取后续原始头文件与测试数据|本地构建和测试不需要网络|
|数据|三个官网手工方案；81案快速集、153案固定种子自建压力集，自带可行性witness|按用户要求自行设置测试，无需等待官方包|

图中1e9级“显存”是int64模拟数量，不会在CPU内存中分配相同大小的真实张量。图存储量与节点、边、方案事件数相关，不能按硬件显存数字估算主机RAM。

本机路径：

- CMake：`C:\Program Files (x86)\CMake\bin\cmake.exe`
- G++：`E:\mingw64\bin\g++.exe`
- Make：`E:\mingw64\bin\mingw32-make.exe`
- Python（仅测试脚本）：`C:\Users\admin\miniconda3\python.exe`

`scripts/build.ps1`临时把MinGW bin目录加入当前进程PATH，确保DLL加载。不修改系统PATH。迁移开发机时替换脚本中的compiler/make路径，或手动选择本机CMake生成器。

```powershell
.\scripts\build.ps1
.\scripts\test.ps1 -Full
ctest --test-dir build --output-on-failure -V
.\build\aicore_demo.exe --reference
```

当前已有标准库JSON输入驱动与独立评测器。可选后续工具：Clang地址/未定义行为Sanitizer、性能采样器和离线小图最优求解工具，不是当前运行必需依赖。
