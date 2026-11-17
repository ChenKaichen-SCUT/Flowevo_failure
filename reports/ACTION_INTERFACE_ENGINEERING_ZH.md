# 动作接口一致性：只报警

审查全部7691条已有action响应，其中7438条对应实际执行动作，253条未进入实际动作序列。没有发起新请求。143条旧格式请求无法恢复结构化公开上下文，标为LEGACY_FORMAT_UNSUPPORTED，不当作新接口错误；其余输入来自当时的请求公开状态。检测器不读取动作后反馈、score、reward或Gold。

|类别|最终筛查数量|解释|
|---|---|---|
|明确reason/action冲突|2|最终显式修正写green box，action仍red box|
|明确目标类型矛盾|4|例如把cup当inclined plane、paint当light bulb|
|材质名/对象别名仍不确定|2|wood等短称不能仅凭词面宣布不是斜面别名|
|focus作为检查的语言候选|68|需人工复核，不能全当确证错误|
|其它动词语义差异候选|6|仅警告，不自动替换动作|
|明确正常措辞差异|44|冠词、公开房门称呼等|
|可能是中间导航步骤|17|先去走廊不等于与最终浴室目标矛盾|

这是候选筛查，不是经过独立标注集验证的准确率、召回率或整体知识错误比例。开发时发现代词、泛称animal和中间导航造成误报，已加入回归约束。生物类别知识（如把potato当animal）仍不是字面接口检查能可靠裁定的范围，明确保留漏检/UNKNOWN。

## focus契约与不干预验证

focus可能推进子目标、完成任务或在错误选择时终止任务；它不是通用观察/测量动作。First focus on thermometer等明确要求仍然合法。共审查522个focus响应，没有设置focus禁令。

新ActionGateway只把interface_audit写入日志。它不改action，不发VETO，不进入重规划提示，也不增加请求。12个TRAIN/DEV真实JVM检查涵盖已知错误、必需focus和正常表述；均重放同一公开前缀并保持原动作与动作后公开哈希一致。错误动作也原样执行，不能把报警误称为已经修复模型决策。

|来源|步|人工参照类别|检测到该类别|
|---|---|---|---|
|discovery-v2.F.06eebbde9128242aba13|10|REASON_ACTION_CONFLICT|True|
|discovery-v2.F.5de4ccea5ffbd8f8b877|8|REASON_ACTION_CONFLICT|True|
|discovery-v2.F.20e65c56c84af8ab157f|1|TARGET_OBJECT_MISMATCH|True|
|discovery-v2.F.81f896325b22612a849e|14|TARGET_OBJECT_MISMATCH|True|
|discovery-v2.F.02e77cda31db3b964346|1|FOCUS_AS_INSPECTION|True|
|discovery-v2.F.1b4703786cd7f2ff0592|46|KNOWLEDGE_REQUIRED_NOT_LITERAL_INTERFACE|False|

以下为按记录ID排序选取的正常措辞样例，不是随机性能测试：

|请求ID|实际action|保存reason|
|---|---|---|
|dev-baseline-v1.F.cfcb5065ead3594fa047.action.0004|open door to hallway|I have an adult bee in inventory. Next, open the closed hallway door so I can travel toward the living room red box.|
|dev-baseline-v1.F.cfcb5065ead3594fa047.action.0007|open door to living room|I have an adult bee in inventory. Next, open the closed living room door so I can carry the bee to the red box there.|
|dev-baseline-v1.F.d18b1fb3c281e62c8cd6.action.0046|go to door to bedroom|I have a bee in inventory; the blue box is likely in the bedroom, so I will enter the bedroom to place the animal there.|
|discovery-v1.F.1b4703786cd7f2ff0592.action.0027|go to greenhouse|The goal is to find an animal. I've checked the art studio, bedroom, kitchen, and bathroom without success. The greenhouse is a likely place for an animal, and its door is now open. Next I'll go to the greenhouse to search.|
|discovery-v1.F.200d3a1c025ac59e0ad7.action.0009|focus on banana seed in inventory|I have a banana seed in inventory and the goal says to first focus on a seed. I'll focus on the banana seed in inventory to begin the growth process.|
|discovery-v1.F.279ad8d80a9088c7546b.action.0004|go to kitchen|Marshmallow is likely in the kitchen. The kitchen door is now open, so I should go to the kitchen to find the marshmallow.|
|discovery-v1.F.4c9a9959a29b533c1f10.action.0002|activate stove|The sink is broken, so I need another heat source. The stove is the natural way to boil water. I'll activate the stove to begin heating.|
|discovery-v1.F.4c9a9959a29b533c1f10.action.0011|look in metal pot|The metal pot is now on the activated stove. To boil water, I need water in the pot; the sink is broken, so I should check available water sources. The fridge has a wood cup containing orange juice, but water is needed. First, I'll look in the metal pot to confirm it's empty, then find water.|
|discovery-v1.F.81f896325b22612a849e.action.0004|go to workshop|The workshop door is open and likely contains the inclined planes for the friction experiment. I'll go to the workshop to inspect them.|
|discovery-v1.F.965d4f1df81ea937ed3b.action.0002|go to hallway|The goal is to find a plant and move it to the purple box. The workshop has no plant visible; the hallway may contain one. I'll go to the hallway to search.|
|discovery-v1.F.965d4f1df81ea937ed3b.action.0004|go to greenhouse|The greenhouse door is open; plants are likely inside. I will go to the greenhouse to find the plant.|
|discovery-v1.F.b305a2703799b76c3a98.action.0030|go to hallway|The green box currently contains only an orange, and the adult bee I previously moved there is no longer visible. I need a living thing; the dead pea plant in inventory is not living. I should inspect the hallway/greenhouse for a living organism, but first check the current room contents. Since the goal says move a living thing to the green box in the bedroom, and no living thing is visible here, I will go to the hallway to search.|

完整逐响应表为results/engineering/action_response_audit.csv，保留原请求ID、实际执行标记、公开输入哈希和警告证据。
