# 共享原链的物理年龄beam（实验候选）

R124按原输入SHA联接现有实际COPY和已审计必要界。ladder8334/8330最多只差4，因此不做新专项；cross_group14合法9755/6993有2762潜在削减上限。C−L只是潜力上限，必要界可能松，不能保证可达。17未输出输入、原336/新72都保留，旧合法输出作为incumbent，不重新运行旧有限预算候选来制造差异。

候选只接受全部SET对应私有ADD/MULW链、共享GET、原GET/SET寄存器唯一读写分离、至多16链。链内原算术严格依赖顺序，但链间逐条算术交错，不将整段branch原子化。GET到首次原使用才出生，完整原节点包括unused GET保留，不重算、不别名、不交换真实有序args。

状态：(所有原链prefix, 已出生GET bitmask, 每个原GET剩余distinct原消费者数, 全部当前live原ID及最新物理年龄, 累积COPY费用, 路径)。prefix覆盖待发原节点和未来链序约束；GET mask防止已经用完身份被再读；remaining控制last-use；每个年龄包含原ID，不能以数值等价或相同角色复用。完全同资源键可保留较低费用路径。这里只用最老到期身份的贪心COPY，未枚举所有COPY时机或GET出生次序。

每个转移发射该链下一条真实原算术，缺GET先按显式固定规则发射；链最后一条随后SET。动作按真实物理距离≤W模拟COPY，每条GET或SET也推进物理槽，当前最后消费身份可直接覆盖。恢复时逐原ID/原有序args materialize并断言COPY费用与模拟一致；此一致是内部检查，还必须独立原JSON身份、符号、三整数重放。

beam以当前COPY加乐观未来根consumer费用排序：已出生根最新年龄a、剩余u个不同原consumer需要的后续自身COPY至少max(0,ceil((a+u−1−W)/(W−1)))；尚未出生根乐观设a=1，sum只计各自身身份COPY。即使改用更老副本也不能减少从当前最新位置到最后消费的乐观跨度。该项仅用来排序，不输出新不可行/最优证书；有限beam丢分支，不是支配证明。另保留cost优先消融。tie使用live个数、剩余根consumer和原prefix稳定排序。状态数、时间、beam有界；无完成候选只能未知/匹配失败，绝不不可行证书。需要完整candidate才可能替代经独立检查的incumbent，COPY更差的结果保留负面记录。理论成本约O(M·B·Q·(W+G))，M算术数、B beam、Q链数、G原根数；原path持久链接避免O(M²)路径复制。实际仍需测常数和校验尾部，不宣称250ms整体墙时。

直接依据：CC2023 move/窗口年龄规则，Chen min-reg共享消费者调度；相比此前root phases自由压力排序及整段branch COPY beam，此候选以逐原算术的真实COPY费用和全部物理身份年龄选择交错。限制范围、失败回退及官方语义边界不变。

官方JSON parser只接受W4/8/16/32。直接构造Block的W1显式拒绝本matcher，即使单GET→MULW(x,x)→SET确实可行也不报全问题无解，避免W−1除零。W2为直接Block边界研究而非官方格式支持，包含共享GET多个消费者和未用GET测试。调用方PreparedGraph必须属于同一Block对象；总搜索预算从PreparedGraph前开始，包含preprocessing、beam、原order恢复及emit，匹配与恢复设置截止检查。时间是有限搜索截止，独立校验/输出与某次Python操作尾部不是硬墙时承诺。
