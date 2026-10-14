# 独立资源预检补充：尚未执行

保留原runner、plan和54份冻结清单，新增revision1，不修改候选源码或金标。修订runner在初次创建G专属目录之前、每个版本/编译/控制/核验命令启动之前，调用Windows GlobalMemoryStatusEx取得实际ullAvailPhys，要求可用物理RAM至少1GiB；同时要求G可用盘至少1GiB、F写小状态余量至少64MiB。全部原始API字段、返回值、异常、F/G total/used/free、UTC、阈值及检查结果单独小JSON记录，状态引用其SHA。

API失败意味着RAM未知，直接阻止新子进程。首次预检失败保留status/raw且不创建compiler或G专属目录；即使F低于64MiB仍尝试写小失败证据，绝不因此放行子进程。初次status本身作为不可重启哨兵，初错或首个实际child非零不覆盖、不自动重跑；后续修订如需执行须另审。对任何记录失败/磁盘写失败默认异常退出，不启动后续child。

只修改各process的TEMP/TMP/TMPDIR，不修改系统设置、不清理用户文件。此为共享功能资源前置条件，不是性能窗口hostload采样或整机空闲证明。原160+16及单文件/仅编译12例范围完全不变。原冻结54文件仍在执行前后逐SHA核对；新增manifest引用旧freeze/runner/plan的实际SHA。
