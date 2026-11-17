# 治理信用和库状态重算

本轮没有调用模型，也没有重新计算或报告任务成功率。冻结的动作、模型输出、编译候选和任务结果均作为外生历史记录。原发布器从冻结Git对象原样提取，先验证再作信用干预。

## 口径与生产代码修复

- **直接信用**：至少执行一个 direct_skill 动作才进入直接使用计数。仅当最后一个直接动作的宿主结果已完成任务，才记直接完成；需要回退的部分执行记不完整尝试，后续动态成功不归给模板。零动作的进入/阻断另记，不计使用。
- **引导信用**：按实际 skill_guided 动作记曝光及整局结果的关联。L2与L3可以同时注入，分别记共同曝光，但原生任务级 guided_total 每局只加一次。不能把共同曝光拆成两个独立因果收益。
- **仅检索**：只记 retrieved / retrieved_only，没有任务结果效用。引导未实际注入时也只算检索。
- 纯holdout需要有动态动作，且没有直接前缀、没有引导动作。混合路径单列。
- 修正后使用 ScienceSkillLibrary 序列化上述账本，batch_runner.publish_batch 已接入；三层检索、直接路径、引导、回退及原生治理阈值仍保留。

没有实际直接使用时，上游 template_utility 初始值仍为1。这是原有准入先验，**不是测得的100%成功率**。本轮没有另造效用学习算法来改善这一先验。

## 重算范围和对照

42个批次、236条正式轨迹的原库状态及发布事件逐项复现。16条discovery-v1工程校准的contrastive_stats无法由最终冻结发布器复现，单列排除库状态因果重算；这些轨迹仍包含在动作响应审查中。没有按结果好坏挑选正式任务。

1. isolated_credit_fix：每个run从原初始库独立修正当前阶段信用，暖库旧错账尚在。
2. chained_credit_fix：从空库重新走TRAIN发布顺序，再按原计划独立分叉，修正信用但保留原闲置计时。
3. chained_credit_and_age_fix：在上一项基础上修正新入库技能的闲置起点，作为本分支默认实现。

仅去掉检索计数，会暴露原先的闲置计时缺陷：未使用模板没有last_used时，旧审计按第0局起算，新入库技能可能立即被判长期闲置。现在记录独立admitted_at；第一次实际使用之前按入库时间计龄，不伪造一次使用。原50局阈值不变。旧库缺失入库时间时不猜测；完整链式重算才有真实发布时刻。

|run|组|重算模式|最终变化模板数|准入变化事件|检索与旧轨迹不相容|
|---|---|---|---|---|---|
|discovery-v2|F|isolated_credit_fix|4|0|0|
|discovery-v2|F|chained_credit_fix|4|0|0|
|discovery-v2|F|chained_credit_and_age_fix|5|0|0|
|selected-train-v1|F|isolated_credit_fix|1|0|0|
|selected-train-v1|F|chained_credit_fix|5|0|0|
|selected-train-v1|F|chained_credit_and_age_fix|6|1|10|
|batch-sensitivity-1-v1|F|isolated_credit_fix|0|0|0|
|batch-sensitivity-1-v1|F|chained_credit_fix|4|0|0|
|batch-sensitivity-1-v1|F|chained_credit_and_age_fix|5|0|2|
|batch-sensitivity-8-v1|F|isolated_credit_fix|0|0|0|
|batch-sensitivity-8-v1|F|chained_credit_fix|4|0|0|
|batch-sensitivity-8-v1|F|chained_credit_and_age_fix|5|0|2|
|dev-baseline-v1|F|isolated_credit_fix|1|0|0|
|dev-baseline-v1|F|chained_credit_fix|6|1|4|
|dev-baseline-v1|F|chained_credit_and_age_fix|6|0|4|
|main-order-17-v1|F|isolated_credit_fix|1|0|0|
|main-order-17-v1|F|chained_credit_fix|6|1|6|
|main-order-17-v1|F|chained_credit_and_age_fix|6|0|6|
|main-order-17-v1|F-I|isolated_credit_fix|2|0|0|
|main-order-17-v1|F-I|chained_credit_fix|7|1|6|
|main-order-17-v1|F-I|chained_credit_and_age_fix|7|0|6|
|main-order-17-v1|F-T|isolated_credit_fix|1|0|0|
|main-order-17-v1|F-T|chained_credit_fix|5|0|6|
|main-order-17-v1|F-T|chained_credit_and_age_fix|6|0|6|
|main-order-17-v1|F-S|isolated_credit_fix|1|0|0|
|main-order-17-v1|F-S|chained_credit_fix|6|1|6|
|main-order-17-v1|F-S|chained_credit_and_age_fix|6|0|6|
|main-order-17-v1|F-H|isolated_credit_fix|1|0|0|
|main-order-17-v1|F-H|chained_credit_fix|6|1|6|
|main-order-17-v1|F-H|chained_credit_and_age_fix|6|0|6|
|main-order-29-v1|F|isolated_credit_fix|1|0|0|
|main-order-29-v1|F|chained_credit_fix|5|0|6|
|main-order-29-v1|F|chained_credit_and_age_fix|6|0|6|
|main-order-29-v1|F-I|isolated_credit_fix|1|0|0|
|main-order-29-v1|F-I|chained_credit_fix|6|1|6|
|main-order-29-v1|F-I|chained_credit_and_age_fix|6|0|6|
|main-order-29-v1|F-T|isolated_credit_fix|1|0|0|
|main-order-29-v1|F-T|chained_credit_fix|5|0|6|
|main-order-29-v1|F-T|chained_credit_and_age_fix|6|0|6|
|main-order-29-v1|F-S|isolated_credit_fix|1|0|0|
|main-order-29-v1|F-S|chained_credit_fix|6|1|6|
|main-order-29-v1|F-S|chained_credit_and_age_fix|6|0|6|
|main-order-29-v1|F-H|isolated_credit_fix|1|0|0|
|main-order-29-v1|F-H|chained_credit_fix|6|1|6|
|main-order-29-v1|F-H|chained_credit_and_age_fix|6|0|6|
|control-order-17-v1|F|isolated_credit_fix|1|0|0|
|control-order-17-v1|F|chained_credit_fix|6|1|2|
|control-order-17-v1|F|chained_credit_and_age_fix|7|1|2|
|control-order-17-v1|F-I|isolated_credit_fix|1|0|0|
|control-order-17-v1|F-I|chained_credit_fix|6|1|2|
|control-order-17-v1|F-I|chained_credit_and_age_fix|7|1|2|
|control-order-17-v1|F-T|isolated_credit_fix|1|0|0|
|control-order-17-v1|F-T|chained_credit_fix|6|1|2|
|control-order-17-v1|F-T|chained_credit_and_age_fix|7|1|2|
|control-order-17-v1|F-S|isolated_credit_fix|1|0|0|
|control-order-17-v1|F-S|chained_credit_fix|6|1|2|
|control-order-17-v1|F-S|chained_credit_and_age_fix|7|1|2|
|control-order-17-v1|F-H|isolated_credit_fix|1|0|0|
|control-order-17-v1|F-H|chained_credit_fix|6|1|2|
|control-order-17-v1|F-H|chained_credit_and_age_fix|7|1|2|

完整修正分支中有6个准入判定变化事件，下面列出全部。**一旦检索不同，后续保存的响应就不能被当作新策略的自然行为。** 重算可以说明在固定历史观察下的库记账/准入/抑制差异，不能说明真实在线任务结果会怎样变化。

|run|组|来源记录|候选模板ID|原→重算准入|首次检索分歧|
|---|---|---|---|---|---|
|selected-train-v1|F|selected-train-v1.F.003597b7b9c549df70c6|sw_9b4527b829af33c8|True→False|selected-train-v1.F.87c6510f7e249ea37105|
|control-order-17-v1|F|control-order-17-v1.F.ce83a66e347b93d9a021|sw_66c8ca7a27d79dc0|False→True|control-order-17-v1.F.ce83a66e347b93d9a021|
|control-order-17-v1|F-I|control-order-17-v1.F-I.ce83a66e347b93d9a021|sw_873741a02e879122|False→True|control-order-17-v1.F-I.ce83a66e347b93d9a021|
|control-order-17-v1|F-T|control-order-17-v1.F-T.ce83a66e347b93d9a021|sw_1298d0ca8e4b3f6d|False→True|control-order-17-v1.F-T.ce83a66e347b93d9a021|
|control-order-17-v1|F-S|control-order-17-v1.F-S.ce83a66e347b93d9a021|sw_db3f68cbc0ea67d7|False→True|control-order-17-v1.F-S.ce83a66e347b93d9a021|
|control-order-17-v1|F-H|control-order-17-v1.F-H.ce83a66e347b93d9a021|sw_c47f0aae57e99291|False→True|control-order-17-v1.F-H.ce83a66e347b93d9a021|

## F组具体效用和抑制差异

|阶段|模板ID|任务类型|原效用|重算效用|原→重算使用数|原→重算状态|
|---|---|---|---|---|---|---|
|discovery-v2|sw_341aba094c300a92|inclined-plane-friction-named-surfaces|1.0|1.0|0→0|suppressed→active|
|discovery-v2|sw_375909cbdb878b28|measure-melting-point-unknown-substance|0.0|1.0|1→0|active→active|
|discovery-v2|sw_61eb0da7d3cc263c|lifespan-shortest-lived|1.0|1.0|1→0|active→active|
|discovery-v2|sw_760a5887e0fce35a|melt|0.0|1.0|1→0|active→active|
|discovery-v2|sw_91f1f70cfb01313c|use-thermometer|0.0|1.0|1→0|active→active|
|selected-train-v1|sw_341aba094c300a92|inclined-plane-friction-named-surfaces||1.0|→0|→active|
|selected-train-v1|sw_375909cbdb878b28|measure-melting-point-unknown-substance|0.0|1.0|1→0|active→suppressed|
|selected-train-v1|sw_61eb0da7d3cc263c|lifespan-shortest-lived|1.0|1.0|1→0|active→suppressed|
|selected-train-v1|sw_760a5887e0fce35a|melt|0.0|1.0|1→0|active→suppressed|
|selected-train-v1|sw_91f1f70cfb01313c|use-thermometer|0.0|1.0|1→0|active→active|
|selected-train-v1|sw_9b4527b829af33c8|inclined-plane-friction-named-surfaces|0.5||6→|active→|
|batch-sensitivity-1-v1|sw_341aba094c300a92|inclined-plane-friction-named-surfaces|1.0|1.0|0→0|suppressed→active|
|batch-sensitivity-1-v1|sw_375909cbdb878b28|measure-melting-point-unknown-substance|0.0|1.0|1→0|active→active|
|batch-sensitivity-1-v1|sw_61eb0da7d3cc263c|lifespan-shortest-lived|1.0|1.0|1→0|active→active|
|batch-sensitivity-1-v1|sw_760a5887e0fce35a|melt|0.0|1.0|1→0|active→active|
|batch-sensitivity-1-v1|sw_91f1f70cfb01313c|use-thermometer|0.0|1.0|1→0|active→active|
|batch-sensitivity-8-v1|sw_341aba094c300a92|inclined-plane-friction-named-surfaces|1.0|1.0|0→0|suppressed→active|
|batch-sensitivity-8-v1|sw_375909cbdb878b28|measure-melting-point-unknown-substance|0.0|1.0|1→0|active→active|
|batch-sensitivity-8-v1|sw_61eb0da7d3cc263c|lifespan-shortest-lived|1.0|1.0|1→0|active→active|
|batch-sensitivity-8-v1|sw_760a5887e0fce35a|melt|0.0|1.0|1→0|active→active|
|batch-sensitivity-8-v1|sw_91f1f70cfb01313c|use-thermometer|0.0|1.0|1→0|active→active|
|dev-baseline-v1|sw_341aba094c300a92|inclined-plane-friction-named-surfaces||1.0|→0|→active|
|dev-baseline-v1|sw_375909cbdb878b28|measure-melting-point-unknown-substance|0.0|1.0|1→0|active→suppressed|
|dev-baseline-v1|sw_61eb0da7d3cc263c|lifespan-shortest-lived|1.0|1.0|1→0|active→suppressed|
|dev-baseline-v1|sw_760a5887e0fce35a|melt|0.0|1.0|1→0|active→suppressed|
|dev-baseline-v1|sw_91f1f70cfb01313c|use-thermometer|0.0|1.0|1→0|active→active|
|dev-baseline-v1|sw_9b4527b829af33c8|inclined-plane-friction-named-surfaces|0.6||10→|active→|
|main-order-17-v1|sw_341aba094c300a92|inclined-plane-friction-named-surfaces||1.0|→0|→active|
|main-order-17-v1|sw_375909cbdb878b28|measure-melting-point-unknown-substance|0.0|1.0|1→0|active→suppressed|
|main-order-17-v1|sw_61eb0da7d3cc263c|lifespan-shortest-lived|1.0|1.0|1→0|active→suppressed|
|main-order-17-v1|sw_760a5887e0fce35a|melt|0.0|1.0|1→0|active→suppressed|
|main-order-17-v1|sw_91f1f70cfb01313c|use-thermometer|0.0|1.0|1→0|active→active|
|main-order-17-v1|sw_9b4527b829af33c8|inclined-plane-friction-named-surfaces|0.5||12→|active→|
|main-order-29-v1|sw_341aba094c300a92|inclined-plane-friction-named-surfaces||1.0|→0|→active|
|main-order-29-v1|sw_375909cbdb878b28|measure-melting-point-unknown-substance|0.0|1.0|1→0|active→suppressed|
|main-order-29-v1|sw_61eb0da7d3cc263c|lifespan-shortest-lived|1.0|1.0|1→0|active→suppressed|
|main-order-29-v1|sw_760a5887e0fce35a|melt|0.0|1.0|1→0|active→suppressed|
|main-order-29-v1|sw_91f1f70cfb01313c|use-thermometer|0.0|1.0|1→0|active→active|
|main-order-29-v1|sw_9b4527b829af33c8|inclined-plane-friction-named-surfaces|0.5||12→|active→|
|control-order-17-v1|sw_341aba094c300a92|inclined-plane-friction-named-surfaces||1.0|→0|→active|
|control-order-17-v1|sw_375909cbdb878b28|measure-melting-point-unknown-substance|0.0|1.0|1→0|active→suppressed|
|control-order-17-v1|sw_61eb0da7d3cc263c|lifespan-shortest-lived|1.0||3→|active→|
|control-order-17-v1|sw_66c8ca7a27d79dc0|lifespan-shortest-lived||1.0|→0|→active|
|control-order-17-v1|sw_760a5887e0fce35a|melt|0.0|1.0|1→0|active→suppressed|
|control-order-17-v1|sw_91f1f70cfb01313c|use-thermometer|0.0|1.0|1→0|active→active|
|control-order-17-v1|sw_9b4527b829af33c8|inclined-plane-friction-named-surfaces|0.5||6→|active→|

其它组及所有模式的逐模板变化见 results/engineering/governance_template_deltas.csv；逐事件审计见governance_events.csv；完整库状态见artifacts/engineering/governance_states.json。ABSENT/空值表示该版本库中不存在，不补成效用0。没有出现引导负迁移抑制的新证据；该原生判据保留，但曝光关联不等于净因果收益。
