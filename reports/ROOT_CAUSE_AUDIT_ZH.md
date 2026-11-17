# FlowEvo–ScienceWorld 根因诊断：阶段 A

结论：**先修正技能表示/绑定接口、动作语义和治理记账；当前证据不足以支持提出新的 FlowEvo 扩展算法。** 没有把原有低分概括为“科学知识不够”，也没有把绑定拒绝全部视为错误。

本轮阶段 A 分析历史 **252 局、7453 个实际动作**。主要基线为 116 局、104 个独立 task/variation/split、3520 动作，42 成功、74 失败，覆盖全部 60 初始 TRAIN、20 额外 TRAIN、8 DEV、24 主 TEST F 和4范围外 TEST F。其余112局其它组、8局重复TRAIN敏感性、16局已废弃工程校准单列，绝不合并当成基线。已公开 TEST 仅作历史分析，未进行新的 TEST 模型求解。

历史提交 `a0f6e0816c23a4abcb646a5fb018e786c2a6be95`。原服务器日志存在，复制所需文件到独立 `input-snapshot/` 后移除写权限，未复制 secrets。复用原统计及回放脚本在独立 recompute 目录运行，summary.json、episodes.csv、costs.csv 与发布版本逐字节一致。服务器分析与 JVM 回放在只有 loopback 的网络命名空间中运行，无法连接外部模型服务。另在本机从公开脱敏记录重建全部分析表，核心汇总及技能链路CSV与私有分析一致；历史费用求和只存在约3×10^-14美元的SQLite浮点尾差，详见零API复算说明。未读取 api.txt、未启动调度器。**新增 DeepSeek 调用 0 次，新增 API 费用 0 元。** 输入与运行回执见 artifacts/root_cause_input_manifest.json、root_cause_run_receipt.json、root_cause_public_reproduction.json。


## 主要发现

1. **技能供给损失与使用时机是具体可定位的问题。** 基线42成功编译候选中27被来源验证拒绝，15通过、8准入；26个拒绝可在逐位置放宽参数一致性后对齐来源，提示同名参数混用/映射错误，但原拒绝正确。主F的12个模板检索均初始拒绝，后续都见到斜面，代码却不重绑。免费晚绑定8候选中6个被未参数化的block阻断，另两个选择不同斜面一胜一负，说明单独放宽绑定不成立。证据：OBSERVED_ERROR及LOCAL_COUNTERFACTUAL_SUPPORTED；整局算法收益NOT_VERIFIED。
2. **大量候选涉及focus被当成观察、错误对象及输出不一致。** 40/116局出现检查性focus语言，31局失败，仅作为候选筛查。6个公开对象相同的look替换避免即时负分但未完成；2例reason写green、action写red，按既有reason替换后完成。证据支持局部执行选择问题，不能证明改善提示后模型会自动修复，也不能外推总体科学能力。
3. **治理错把未执行模板归入整局信用。** 主要基线26条记录，其他组55条，直接路径未进入仍记usage/success。它是可复现工程归因缺陷，不是新算法成果。不能据此声称已导致本轮主TEST失分。

L2/L3确有真实引导，部分内容把focus描述为观察摩擦，存在负迁移风险；但原模型的动态轨迹已出现同类误用，现有少量holdout不足以识别引导的净效应。长程记忆截断也未被隔离：重复可见动作1300次，其中1072次前次反馈仍在16步内，不能自动归因于长程遗忘。

## 数据与证据等级

|总体|轨迹|成功|失败|动作|
|---|---|---|---|---|
|OTHER_ARM_DESCRIPTIVE|112|52|60|3297|
|PRIMARY_BASELINE|116|42|74|3520|
|REPEATED_TRAIN_SENSITIVITY|8|3|5|123|
|SUPERSEDED_ENGINEERING|16|5|11|513|

全部模型请求/Token均从旧记录读取，费用列是历史调用量，不是本轮新增费用。因果标签严格区分观察错误、合理解释、局部动作替代支持和未验证的在线效果。全部18个免费对照在TRAIN/DEV进行，36分支前缀哈希一致。2个动作替换完成任务不是重新取得的模型成绩，不能加到历史成功率中。

## 交付与复算

- [失败分类](FAILURE_TAXONOMY_ZH.md)：252局数据库，终止/中间错误/上游根因分层。
- [技能链路与代表性案例](SKILL_REUSE_BOTTLENECK_ZH.md)：13个具体案例及候选/检索明细。
- [知识、规划和状态](PLANNING_KNOWLEDGE_STATE_AUDIT_ZH.md)：逐步证据、成功失败配对与不可归因之处。
- [局部反事实](CAUSAL_DIAGNOSTICS_ZH.md)：全部18案例，含无效及负面结果。
- [至多三个后续问题](NEXT_RESEARCH_DECISION_ZH.md)：可证伪条件、工程优先和0元最小核验。
- [零API复算步骤](ROOT_CAUSE_REPRODUCE.md)。输入manifest、规则说明、运行回执和CSV均随分支提供，历史报告/运行时/评分脚本未改。

**新增 DeepSeek API 调用：0。新增 API 费用：0 元。阶段 B：未执行。**
