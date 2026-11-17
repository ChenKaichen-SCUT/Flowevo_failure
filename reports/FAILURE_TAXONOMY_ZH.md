# 失败分类：直接终止、可见错误和可能根因

本轮阶段 A 分析历史 **252 局、7453 个实际动作**。主要基线为 116 局、104 个独立 task/variation/split、3520 动作，42 成功、74 失败，覆盖全部 60 初始 TRAIN、20 额外 TRAIN、8 DEV、24 主 TEST F 和4范围外 TEST F。其余112局其它组、8局重复TRAIN敏感性、16局已废弃工程校准单列，绝不合并当成基线。已公开 TEST 仅作历史分析，未进行新的 TEST 模型求解。

历史提交 `a0f6e0816c23a4abcb646a5fb018e786c2a6be95`。原服务器日志存在，复制所需文件到独立 `input-snapshot/` 后移除写权限，未复制 secrets。复用原统计及回放脚本在独立 recompute 目录运行，summary.json、episodes.csv、costs.csv 与发布版本逐字节一致。服务器分析与 JVM 回放在只有 loopback 的网络命名空间中运行，无法连接外部模型服务。另在本机从公开脱敏记录重建全部分析表，核心汇总及技能链路CSV与私有分析一致；历史费用求和只存在约3×10^-14美元的SQLite浮点尾差，详见零API复算说明。未读取 api.txt、未启动调度器。**新增 DeepSeek 调用 0 次，新增 API 费用 0 元。** 输入与运行回执见 artifacts/root_cause_input_manifest.json、root_cause_run_receipt.json、root_cause_public_reproduction.json。


|总体|轨迹|成功|失败|动作|
|---|---|---|---|---|
|OTHER_ARM_DESCRIPTIVE|112|52|60|3297|
|PRIMARY_BASELINE|116|42|74|3520|
|REPEATED_TRAIN_SENSITIVITY|8|3|5|123|
|SUPERSEDED_ENGINEERING|16|5|11|513|

`failure_taxonomy.csv` 每局一行，保留成功局以防仅观察失败导致偏差。`trajectory_decision_audit.csv` 每个实际动作一行，含目标、动作前 look/inventory/上次反馈、模型保存的 reason、动作后反馈和原记录 ID。证据引用 `episodes/<job_id>.json#/steps/<零基下标>`；行号 step 为一基。完整来源仍可用历史公开压缩记录恢复。

主要基线直接终止分布：{"ENVIRONMENT_STEP_LIMIT": 1, "HOST_STEP_LIMIT": 14, "NEGATIVE_SCORE": 59, "SUCCESS": 42}。59 次负分终止中，59 次末条反馈为 You focus on；它是终止行为的关联描述，不能据此宣布所有 focus 都错误。成功局同样需要合法 focus。

|可见标签（多选）|出现局数/116|其中失败局数/74|
|---|---|---|
|AMBIGUITY_MENU|11|9|
|CLOSED_ACCESS_FEEDBACK|21|15|
|ELECTRICAL_TERMINAL_SYNTAX_FEEDBACK|2|2|
|FOCUS_AS_INSPECTION_LANGUAGE_CANDIDATE|40|31|
|IMMOVABLE_OBJECT_FEEDBACK|1|1|
|NEGATIVE_TERMINAL_STEP|59|59|
|REPEATED_ACTION_SAME_VISIBLE_CONTEXT|60|39|
|UNRECOGNIZED_COMMAND_FEEDBACK|15|11|

标签来自明确反馈或保守字符串规则，非模型批量主观标注。CLOSED_ACCESS、UNRECOGNIZED_COMMAND、ELECTRICAL_TERMINAL 等指环境实际报告的局部问题；歧义菜单本身不是错误，正确数字选择是允许动作。FOCUS_AS_INSPECTION_LANGUAGE 是词汇候选，不等于已经证实的误用。重复仅表示动作、look、inventory和返回观察相同，可能仍有不可见时间变化；排除了 wait/activate/deactivate，仍不能将其全部归为无效。

上游根因允许 UNKNOWN / MULTIPLE_PLAUSIBLE_CAUSES。不能将 NEGATIVE_SCORE、100步耗尽或一个正则命中直接当作“缺少科学知识”。`causal_conclusion` 保守保留 INSUFFICIENT_EVIDENCE，局部反事实支持另见 minimal_counterfactuals.csv，不把局部存活当整局获胜。

六个检查型 focus 案例 CF01–CF06 用同对象 look at 替代，均避免当步负分终止，但没有任何一局因此在窗口内完成。这为动作语义/目标落地问题提供局部因果证据，不能估计一个改进提示词能恢复多少全任务成绩。所有未人工核查的类别均只作筛查，不声称可靠自然误判率。
