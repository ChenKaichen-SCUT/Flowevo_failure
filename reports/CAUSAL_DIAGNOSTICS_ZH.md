# 免费最小反事实诊断

冻结计划见root_cause_counterfactual_plan.json；18个检查点/映射案例、36条本地JVM分支，来自14个独立TRAIN/DEV轨迹。所有分支reset，逐步重放来源前缀并核对公开哈希，再执行最多3个已确定动作；有些只剩2步。没有TEST回放、没有新模型规划、没有Gold。完整动作/反馈/宿主结果见minimal_counterfactuals.csv与receipts。

|案例|假设|来源|前缀动作数|事实分支最终分|替代分支最终分|原直接执行检查阻断动作|
|---|---|---|---|---|---|---|
|CF01|H2_FOCUS_SEMANTICS|discovery-v2.F.02e77cda31db3b964346|0|-100|0|无|
|CF02|H2_FOCUS_SEMANTICS|discovery-v2.F.0ef2ea6f576b10fb9a37|1|-100|0|无|
|CF03|H2_FOCUS_SEMANTICS|discovery-v2.F.20e65c56c84af8ab157f|0|-100|0|无|
|CF04|H2_FOCUS_SEMANTICS|discovery-v2.F.81f896325b22612a849e|13|-100|0|无|
|CF05|H2_FOCUS_SEMANTICS|discovery-v2.F.d129caa70cba348ea3e4|15|-100|7|无|
|CF06|H2_FOCUS_SEMANTICS|discovery-v2.F.1b4703786cd7f2ff0592|45|-100|25|无|
|CF07|H2_REASON_ACTION_MISMATCH|discovery-v2.F.06eebbde9128242aba13|9|-100|100|无|
|CF08|H2_REASON_ACTION_MISMATCH|discovery-v2.F.5de4ccea5ffbd8f8b877|7|-100|100|无|
|CF09|H3_NAVIGATION_LOOP|discovery-v2.F.3c034ff32bf35c264df7|98|17|17|无|
|CF10|H3_NAVIGATION_LOOP|discovery-v2.F.ef2e54dbb3a42029c804|98|75|75|无|
|CF11|H1_DELAYED_BINDING|selected-train-v1.F.098816d79aa10bdc5eec|2|100|10|connect block to inclined plane with a rubber surface|
|CF12|H1_DELAYED_BINDING|selected-train-v1.F.098816d79aa10bdc5eec|2|100|10|connect block to inclined plane with a steel surface|
|CF13|H1_DELAYED_BINDING|selected-train-v1.F.17c9fd4a9e6176a23caf|6|10|10|connect block to inclined plane with a plastic surface|
|CF14|H1_DELAYED_BINDING|selected-train-v1.F.17c9fd4a9e6176a23caf|6|10|10|connect block to inclined plane with a platinum surface|
|CF15|H1_DELAYED_BINDING|dev-baseline-v1.F.3ea7c55db1ecffae3c8a|5|100|-100|无|
|CF16|H1_DELAYED_BINDING|dev-baseline-v1.F.3ea7c55db1ecffae3c8a|5|100|100|无|
|CF17|H1_DELAYED_BINDING|dev-baseline-v1.F.722d467db63128d43cf2|13|100|10|connect block to inclined plane with a glass surface|
|CF18|H1_DELAYED_BINDING|dev-baseline-v1.F.722d467db63128d43cf2|13|100|10|connect block to inclined plane with a steel surface|

H1：8个晚绑定候选中6个因字面block无法对应brick被原有效动作接口阻断，另2个同状态选不同斜面得到100和-100。**否定“仅延后绑定就足够”**，支持对象参数覆盖与答案选择缺口。初始拒绝本身合理，暴力放宽不是修复。唯一成功替代不是可部署的参数选择器，不能挑它报泛化收益。

H2：6个同对象focus→look at在相同前缀均避免当步负分，0个完成任务；另2个只执行原reason已经写出的green box动作，均完成。这只证明两个给定动作替换的效果，不证明模型在新提示/新解析下会自然产生该动作，也不证明8例代表总体。

H3：2个局部路线替换均进入未访问房间，分数未变且最终预算结束。说明现有动作预算内有可执行的探索分支，但未验证到达目标或整局收益，也未隔离状态遗忘与规划策略。

证据等级：环境原反馈/代码执行事实为 OBSERVED_ERROR；上游机制解释为 PLAUSIBLE_CAUSE；相同前缀的动作替换结果为 LOCAL_COUNTERFACTUAL_SUPPORTED；模型在修复后的行为、完整新任务收益为 NOT_VERIFIED。CSV的LOCAL_COUNTERFACTUAL_SUPPORTED只表示分支发生不同可见后果，绝不意味着正向收益。

计划构建阶段先发现“走廊可直达浴室”的诊断者假设与公开look不符，改为不假定目标路线的未访问邻室测试；均发生在成功写出计划及执行分支之前。第一次进程池启动因函数名被字符串遮蔽而未执行，修复后按同一冻结计划执行。技术失败不产生收费请求，不是挑分支重跑。

另有6个纯Python治理夹具：每条真实主F记录各自从同一M0出发，比较原记账函数与仅在实际直接执行时记账的门控，前者usage均加1、后者均不变。该结果只支持信用更新差异，不属于上述36条JVM分支，也不证明历史准入/抑制或最终成绩变化。

没有继续追加block→brick后看哪个映射赢的尝试，也没有修改原runtime。逐位置来源参数重绑属于另一个静态工程检查，26/27拒绝候选可对齐来源，并不等同于26个自然可用技能。
