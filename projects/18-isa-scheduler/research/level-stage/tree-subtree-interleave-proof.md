# 固定两子树次序的物理年龄 DP（R158 实际实现范围）

这是严格身份模型中受限候选族的正确性与局部覆盖说明，不是任意树全局 COPY 最优算法。

前提：`match_forest` 接受的完整无共享 GET/SET/ADD/MULW 森林；GET 地址各不同、SET 地址各不同且与GET不相交；无memory order deps；各非SET身份最多一个distinct直接consumer（同一指令重复两个参数仍一个consumer）；不含原COPY/死算术。parent为二元节点；至少一个child含真实二元分支。两side原序列从保存合法order投影，parent整个子树在保存order是连续区间，且parent最后。未用GET、其他roots/SET及完整prefix/suffix都保留。

## 状态充分性

side A/B各只准下一原指令，两个prefix唯一确定local completed集合。local出生且unique consumer未发射的身份必须live；两side根的consumer parent在出口前未发射，故保留。静态users构建去重，不把重复操作数当两份身份。

external是实际物理prefix中已发射且仍有未来消费者的身份。子树定义包含全部原数据祖先，故external不可能被子树内部发射消费；本地全程保留它们。不是将外部排序依赖当temp身份；matcher已排除寄存器hazard，通用图不借此结论。

state为两个prefix与确定role序列中每个live身份的latest副本年龄。候选族只引用latest副本，死槽/较老同身份副本不影响这一族下一转移；不会据此声称最优输出必引用latest，或所有早COPY都可删除。给定同完整state，下一原节点/其有序args/将最后消费的身份及下一槽位置年龄变化完全相同。故仅同完整state保留最小local COPY成本是安全的；prefix总和严格增加，DP为有限DAG。没有逐项年龄支配、身份等值别名或角色对称排序。

## 转移与物理恢复

本节点将消费的全部distinct operands是其唯一最后数据消费（纯树前提）。若最老live年龄=W且不被消费，COPY其latest副本，令该身份年龄1，其它live年龄+1；每COPY占真实槽。若最老即本节点最后消费身份，可以立即发射原节点并将该身份删除；未被消费身份年龄+1，新原输出年龄1。

最多W次循环安全界：物理latest出生槽互异，年龄也互异。若live<W，存在死槽，或本原指令至少最后消费一个live，可以在至多W−1旋转后发射；若满W且本节点不消费live，推进槽必丢一个future身份，受限转移为空。此局部空路径不是原图全局不可行证书。

两side次序均已topological；side间无共享数据或hazard，所以任选下一side依赖仍成立。原数据args按真实原node逐有序引用恢复，重复两个引用保留；相对动作 `(side,offset)` 唯一映射实际原节点。实际实现第一阶段没有跨图缓存，也没有把当前图真实ID作为跨图cache键。每个original恰一次，GET/SET地址、prefix原物理输出及其他原order均保留。DP局部COPY成本须等于实际full-block emitter重放局部成本，否则断言终止。

parent消费两根，再逐原发射原suffix。各出口虽有相同局部成本，external ages可能不同，从而后续COPY不同，因此第一阶段恢复最多16完整出口并按完整block成本选最佳。出口限制按明确cost/age排序，是搜索族截断而非数学支配；truncated统计保留，不能在truncation时称所有完整block最优。500ms包含parse/matcher、实际prefix恢复、DP、出口完整emit；20k是处理DP状态的上限；独立验证成本另外记录。

## 已取得与未取得的证据

R158的20尝试/2完整64输入，20completed、0unknown；保存104完整出口和2原baseline。根代理以raw原JSON独立重放106输出，identity、有序参数、W、COPY和hazard全部通过。ragged64父59单次完整23→21；其它5父提案单次23→22，不相加；指定padded父60仍21→21。

“真实减少”目前已成立；“减少优于两种完整串行次序”尚待直接对照。已保存pure-serial出口不代表覆盖两concat路径，因为相同state可被更低成本混合路径替换。下一控制仅两种串行的独立原JSON发射，不运行新DP、不替换原baseline；若反串行同样可21，不把这2条全归因于一般交错。阶段2与旧48/新36尚未授权/运行。
