# 知识、规划、状态与适配的区分

主要基线有74失败局；59为官方负分结束。40/116局出现 focus 与 inspection/reveal/examine 等词同时出现的候选，其中31局失败。筛查词不能替代人工判断。具体反例：

- discovery-v2.F.20e65c56c84af8ab157f 第1步：目标red light bulb，却focus on red paint in cup；reason说这是最近的红色物体。公开反馈确认聚焦的是paint。这首先是对象落地和动作语义问题，不是不会搭电路的证据。
- discovery-v2.F.81f896325b22612a849e 第13–14步：看到ceramic cup后把杯子当ceramic inclined plane并focus，负分终止。说明名称/材质相近不代表目标实例相同。
- discovery-v2.F.1b4703786cd7f2ff0592 第45–46步：看见potato后称其为animal-like candidate，聚焦后失败。植物性食物是“动物”的论据明确错误；这是一个生物类别知识/目标匹配案例，不能外推为科学知识主导全部失败。
- discovery-v2.F.06eebbde9128242aba13 第10步及 discovery-v2.F.5de4ccea5ffbd8f8b877 第8步：reason最后都明确说green box，但JSON action却是red box。替换为保存reason中的动作，免费同前缀回放均完成。这是输出字段不一致，不是缺少正确颜色知识。解析器忠实执行action，没有错改模型答案。自动读取reason改action仍是待设计工程修复，本轮未部署。
- 未知物质案例还将10°C当前温度称为melting point；一次室温读数不等于熔点测量。即使该分支选green能过官方任务，也不证明实验设计正确。已成功轨迹也可能包含这类shortcut，成功编译不能以“整局成功”为唯一语义质量证据。
- discovery-v2.F.d99ba311a7e8ca9d2161 第99–100步：连接switch到battery两极时持续收到需要指定polarized contact points的反馈。这是接线接口/实验设计问题的直接证据，不足以断言模型不懂电学概念。

## 长程状态假设的反证约束

主要基线有1300个重复动作/相同可见上下文事件，1072个上一次同类反馈仍在最近16步范围内。特别是 find-plant 的3c034ff32bf35c264df7 与 find-living-thing 的ef2e54dbb3a42029c804，在最后两步重复卧室/走廊循环，reason仍称需要去bathroom。走廊公开出口没有bathroom，但有未访问邻室；不能手工假定存在直达浴室门。CF09–10仅用公开出口去未访问art studio，摆脱循环而分数不变，预算仍结束。

StateTracker 只保留最近16条完整反馈，更早仅动作，因此历史状态丢失是合理竞争假设；但短周期重复即使在16步内仍出现，不能把规划停滞全部归因于上下文截断，也不能据此声称加长记忆必有收益。公开view不是完整物理状态，不能将同look当成绝对同状态。

## 成功/失败配对

先列每类一对初始TRAIN成功/失败的最早动作差异，以便定位，再解释有意义的决策而不做跨variation因果归因：

|任务|成功记录|失败记录|首个动作差异步|成功侧动作|失败侧动作|
|---|---|---|---|---|---|
|find-animal|discovery-v2.F.def63cb9dcbcef266a65|discovery-v2.F.1b4703786cd7f2ff0592|1|open bee hive|open drawer|
|find-living-thing|discovery-v2.F.b305a2703799b76c3a98|discovery-v2.F.ef2e54dbb3a42029c804|1|focus on adult pea plant|focus on adult peach tree|
|find-plant|discovery-v2.F.965d4f1df81ea937ed3b|discovery-v2.F.3c034ff32bf35c264df7|1|open freezer|open door to hallway|
|inclined-plane-friction-named-surfaces|discovery-v2.F.5bfedeb6e825464e626d|discovery-v2.F.81f896325b22612a849e|1|look in drawer|look in bowl|
|inclined-plane-friction-unnamed-surfaces|discovery-v2.F.9cef108e88fa0d6aff89|discovery-v2.F.7ed64659a572c6ec8c7f|2|look around|go to hallway|
|lifespan-longest-lived|discovery-v2.F.2dcdca293d9b16367852|discovery-v2.F.548c37117aa7a7208d43|7|look at giant tortoise egg|look at chameleon egg|
|measure-melting-point-unknown-substance|discovery-v2.F.3fbe681bf784f2d76d21|discovery-v2.F.5de4ccea5ffbd8f8b877|1|open door to kitchen|open door to hallway|
|melt|discovery-v2.F.6aebd9fb1322c1074fb6|discovery-v2.F.b22651ad67c9301bcba8|1|open door to kitchen|focus on orange|
|use-thermometer|discovery-v2.F.2beaa66b5bcd3db3dc64|discovery-v2.F.8e96186d11e9af5659e3|1|focus on thermometer|open door to kitchen|

这些pair的目标参数或起始房间可能不同（完整字段见success_failure_pairs.csv）。斜面成功例5bfedeb6e825464e626d最终到达真正斜面，失败81f896325b22612a849e把杯子当目标；最早有解释意义的差异是目标对象验证，而不是机械地把第一步差异当原因。find-animal 的配对中，失败1b4703786cd7f2ff0592选择土豆，成功侧实际找到并转移动物，不能仅因成功访问了某房间就认定强制走同一路线能修复失败。熔点一对的差异还含阈值和颜色映射，必须使用各自目标。

本轮没有任何“离线删除技能提示后模型表现”的虚构实验。关于引导负迁移的净效应、记忆长度净效应以及科学知识不足在总体中的因果占比，均为 INSUFFICIENT_EVIDENCE。
