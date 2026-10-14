# 可选TypeScript上下文适配

Node.js 20+，TypeScript固定6.0.3。编译器API文档说明目前的API适用于7之前版本，因此没有按npm最新版本自动升级。依赖及完整性由package-lock.json固定。

```powershell
.\scripts\setup-typescript.ps1
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_typescript_context.py -v
```

Python调用 `TypeScriptContext.analyze(files, pinned_files)`，输入为规范化相对路径到源码的字典，输出为 `Item` 元组、依赖图、诊断和分析耗时，可直接交给治理核心及 `PreparedContext`。后端只读取虚拟源码并分析AST和符号，不执行输入源码、不进行网络访问。

完整顶层声明保留原文字节对应的文本，包括Unicode、装饰器和注释。运行时导入完整保留被导入模块，初始化、类、静态块和变量声明保守进入闭包。仅当具名 `import type` / `export type` 的目标由纯类型、函数声明及类型导入构成时，使用符号闭包保留所需类型和继承引用；namespace及含潜在初始化的目标仍保留完整模块。

动态路径、未解析的相对模块或语法错误触发整个提供工程的保守保留。ArkTS专用语法例如 `struct` 通常走此回退；这不是完整ArkTS编译器或DevEco插件。SDK、外部包、tsconfig path aliases、反射和真实工程构建仍需要集成。没有把TypeScript静态验证算进Python模型质量分数。

每个调用者拥有独立持续worker，完整分析结果仅缓存上一份完全相同的输入；关闭实例释放状态。改动源码或保护文件立即重新分析。编辑后的编译器可复用上份工程中内容完全相同的SourceFile和oldProgram，但每次重新解析导入，重新构造闭包与治理。`use_cache=False`禁用完整结果缓存，编译器对象复用仍有效；warm命中不包括首次索引成本。Python锁保证同一worker的请求/响应不会串线；进程崩溃报错，当前尚无请求超时/自动重启。

证据：`artifacts/typescript-context-v15.json` 为包含IPC和治理的8工作负载、11轮配对，温热中位加速2.21倍、最小1.73倍；使用字节预算，没有模型推理。`artifacts/typescript-type-import-v16.json` 单列真实Qwen Token预算下的类型闭包对照。功能测试实际编译保留代码并执行，检查跨模块类型、初始化、缓存编辑与Unicode、动态/ArkTS回退。

增量证据 `artifacts/typescript-incremental-v18.json`：26个正反向编辑（文件增删/导入失效、类型继承、初始化、错误/动态/ArkTS回退、Unicode与保护项）与冻结旧worker完全等价；8种128–8192声明/1或8文件各11配对，编辑后IPC+索引+治理中位加速1.34倍，最小1.29倍，整批29.85秒。事先旧快照构造在计时外，所有完整结果缓存禁用。候选额外通过相同5项真实tsc/Node语义测试后提升为默认。8192声明Node驻留点观测约303–304MiB、旧298–300MiB，不宣称降低RSS峰值。冻结版本在 `research-candidates-v18`，基线worker仅统一为LF行尾、文本与原版逐字符核对。

官方参考：[Compiler API](https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API)、[Modules reference](https://www.typescriptlang.org/docs/handbook/modules/reference.html)。
