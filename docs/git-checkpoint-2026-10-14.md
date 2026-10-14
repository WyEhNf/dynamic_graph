# Git基线：2026-10-14

工作区现在以`F:/Hackathon`为Git工作树，主分支为`main`。F盘余量不足，Git对象目录通过`.git`文件指向`G:/Hackathon-git/hackathon.git`。备份时应同时保存工作树与该Git对象目录。

首个提交保存四项目当前实现、工具脚本、文档、探索报告及工作区关键摘要。第19题当前S33的19页报告、轻量证据ZIP、验证汇总和阶段JSON纳入版本控制；完整206源、两套新构建的测试记录及复现脚本位于证据ZIP中。大型矩阵、下载模型、虚拟环境、构建产物和历史生成语料由`.gitignore`排除，保留原文件与既有证据路径，不通过Git复制数GB数据。

第19题基线CLI为`912c9fec8ac5e1793d6217afc5c3b09f49a8b8e536f273eeaef9b94a69072eba`，core为`e7c9dd7fa08ecff90318762fd3bef95e816f7918e85e9ec2274bebca21c3b3c6`。本地全量测试、源码/对象/PE内容桥接与行业对照见`projects/19-dynamic-graph/reports/project19-exploration-validation-summary.json`及同目录证据包。

原始矩阵和性能/验收目录位于`G:/Hackathon-stage2-artifacts/project19/`及项目原`artifacts/`；各冻结报告保留输入、原C真值、实际产物的SHA256。历史实验源码中保留的失败候选不代表当前产品已采用；生产源码与阶段决策分别记录。

本轮后续改动将另作提交，主测试负载限定为实际Cholesky源码；通用VM与非法输入只作为兼容/拒绝控制。当前没有配置远程仓库，不进行外部推送。
