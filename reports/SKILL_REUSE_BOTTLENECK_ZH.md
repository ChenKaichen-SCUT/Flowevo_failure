# 成功技能复用瓶颈专项审计

主要基线独立统计：42 个成功轨迹产生42候选/42引导，27模板被来源验证拒绝，15模板通过，8获原生库准入。7个有效候选因同类型已有活跃且 utility≥0.5 的模板被拒；这是一类型一个模板的原生策略，不是每个新技能都会新增入库。其它组、敏感性和工程校准另见 root_cause_summary.json。

29次模板检索对应29次初始绑定请求，26拒绝、3接受。主 TEST F 12次模板检索全为斜面类型，0绑定接受；这12次在后续公开轨迹中全部出现斜面。初始拒绝有合理性：对象当时不在眼前；但 run_episode 仅启动时调用 bind_skill，后续执行循环不再检索/绑定。它解释了该实现中“后来满足可见性也不会进入L1”的机制，不证明重绑后一定能完成任务。

## 生成、来源验证与准入

27个拒绝中26个可通过逐位置重新匹配占位符对齐来源动作，16个在贪心匹配候选中出现同名参数对应不同字符串。这个静态诊断放宽的是来源对齐的参数一致性，不是执行安全检查；不能自动产生合格可迁移技能，也不能证明每一处字符串差异都要求不同对象参数。不同房间 hallway / greenhouse / outside 被压成同一个 room 是明确的表示风险；动物的不同称呼也可能是别名，或存在其它合法对齐。原拒绝的是给定example_bindings实例化后的序列，直接放宽来源检查不成立。另一例存在无法与来源动作序列对齐的字面/顺序问题。CSV字段 collapsed_parameter_values 保存的只是这项贪心诊断候选，不能作为自动错误裁定；S02是已通过来源验证却仍出现字符串差异的反例。

`ScienceCompiler` 要求模型生成 applicability，但构造 AlfWorldSkillTemplate 时没有保存该字段，运行绑定只看到模板/参数/示例值和当前公开状态。代码见 src/flowevo_sw/flowevo_adapter.py。丢失条件是可观察适配限制，实际效应尚未隔离。检索由上游 SkillLibrary 按精确 task_type 返回一个模板，不检查最少/最多摩擦、目标材料或新房间路线；同类相关不等于当前可用。

## 绑定之后仍存在什么问题

固定斜面模板 sw_9b4527b829af33c8 是 look at {plane} → connect block to {plane} → focus on {plane}。来源目标是 titanium/zinc 的最少摩擦，source episode selected-train-v1.F.003597b7b9c549df70c6 第1–5步完成。它保留了字面量 block，只参数化 plane，没有保存“如何在两个候选中选择”的实验/判断过程。来源反馈显示 terminal 连接，没有摩擦测量读数；成功评分并不证明该序列是完整科学实验。

免费 H1 对4个 TRAIN/DEV 状态枚举两块可见斜面，共8候选：6个被原 valid-action 检查拦在 connect block（当前物体为 brick）；另外2个可执行，选glass成功、选brass负分结束。因此“把绑定改晚”不足以修复：还涉及遗漏物体参数与把待判断答案提前塞进 plane 参数。不得从两块斜面的宿主得分挑赢的映射用于模型。这是诊断，不是8个新泛化测试。

有明确正确拒绝：未知物质/温度计不在当前房间，不能凭来源值填对象；最长/最短寿命技能不能照抄来源动物。在 control-order-17-v1.F.ce83a66e347b93d9a021 中，绑定 reason 明说从示例拿 chameleon egg，当前并未看到该动物，却被接受。这说明接受器只验证布尔值和参数非空，不验证每个映射的公开来源；不能把所有未执行都归为“过度保守”。该局先执行2个导航动作，随后在不可用动物动作前回退，避免强行错误目标。

## 治理记账的确定缺陷

batch_runner.publish_batch 在检索 best_layer==1 时无条件 record_template_usage(template_id, trace.success)，没有要求 direct_use_count>0。主要基线26个未进入直接路径的局仍给L1记了整局成功/失败，其他组55局同类。实际主要基线直接路径仅3次：非生物任务5动作直接成功，最短寿命TRAIN因已在outside在第一个导航动作前回退（0动作），范围外TEST先执行2动作后回退。不能用未执行模板的整局结果解释它的直接效用。主 TEST 期间80→92未到下一次20局周期审计，故不声称此错账已造成主TEST抑制或分数下降；它首先损害治理的归因可信度。

本轮另对6条真实主F记录执行同一M0库副本夹具：原 publish_batch 将 usage 从6变7，仅增加 direct_use_count>0 门控后保持6，见 root_cause_governance_fixtures.json。这是 LOCAL_COUNTERFACTUAL_SUPPORTED_ACCOUNTING_ONLY；不是整轮库演化或在线成绩回放。

## L2/L3 是否帮助或造成负迁移

确实使用了引导，未静默退化为空库。guidance_descriptive.csv 按任务类型区分引导/无引导，保留真实 holdout。主F只有2个无引导局，不能用跨阶段总成功率或删除提示词伪造因果对照。

明确的风险例：main-order-17-v1.F.36fece574b8499e3aace 检索了来源 70bab2789294b9804cf0 的引导，文字声称 focus 是 observe/measure friction，并建议对另一斜面重复 connect-and-focus；但 focus 有终止任务的语义。它是可见的不可靠指导内容，与模型本身已有误用竞争解释；尚不能证明这条指导诱发了该局错误。另一个引导正确提示先开门、再移动，动作中亦出现该次序，仍不能把一般常识重合算作因果帮助。

上游 L3 的位置统计解析器仍为 `take ... from ...`，ScienceWorld 多用 pick up/move，可能丢失位置抽取；这是接口适配不匹配，不等于已证明主要失败来自L3。需要先用免费解析器回放测试，不必先提出学习算法。

## 代表性案例（13个环节案例，来自12条独立轨迹，全部保留原记录 ID）

### S01 `control-order-17-v1.F.8828fcd18aa5694e5861`

事件 `COMPILATION`，来源 `compilations/control-order-17-v1.F.8828fcd18aa5694e5861.json`。来源目标：Task Description:
Your task is to find the animal with the shortest life span.  The animals are in the 'outside' location.  Focus on the animal with the shortest life span.

当前目标：成功轨迹编译阶段

模板：`["open door to {room}", "go to {room}", "go to {room}", "open door to {room}", "go to {room}", "open door to {room}", "go to {room}", "look at {animal_egg}", "look at {animal_egg}", "look at {animal_egg}", "focus on {animal_egg}"]`

来源验证：not an observed action subsequence；首个不能按既定映射对齐的动作：open door to hallway。逐位置对齐发现同名参数取值：{"animal_egg": ["chameleon egg", "frog egg", "parrot egg"], "room": ["greenhouse", "hallway", "living room", "outside"]}。准入：False（SOURCE_VALIDATION_FAILED）。

### S02 `dev-baseline-v1.F.cfcb5065ead3594fa047`

事件 `COMPILATION`，来源 `compilations/dev-baseline-v1.F.cfcb5065ead3594fa047.json`。来源目标：Task Description:
Your task is to find a(n) animal. First, focus on the thing. Then, move it to the red box in the living room.

当前目标：成功轨迹编译阶段

模板：`["open {container}", "focus on {animal}", "pick up {animal}", "open {door}", "go to {room}", "move {animal} to {receptacle}", "look in {receptacle}"]`

来源验证：通过；首个不能按既定映射对齐的动作：无。逐位置对齐发现同名参数取值：{"animal": ["adult bee", "bee 0"]}。准入：True（ADMITTED）。

### S03 `discovery-v2.F.2dcdca293d9b16367852`

事件 `COMPILATION`，来源 `compilations/discovery-v2.F.2dcdca293d9b16367852.json`。来源目标：Task Description:
Your task is to find the animal with the longest life span.  The animals are in the 'outside' location.  Focus on the animal with the longest life span.

当前目标：成功轨迹编译阶段

模板：`["open {door}", "go to {room}", "open {door}", "go to {room}", "open {door}", "go to {room}", "look at {animal}", "focus on {animal}"]`

来源验证：not an observed action subsequence；首个不能按既定映射对齐的动作：open door to hallway。逐位置对齐发现同名参数取值：{"animal": ["egg giant tortoise", "giant tortoise egg"], "door": ["door to greenhouse", "door to hallway", "door to outside"], "room": ["greenhouse", "hallway", "outside"]}。准入：False（SOURCE_VALIDATION_FAILED）。

### S04 `discovery-v2.F.31452f59c48bc5d93974`

事件 `COMPILATION`，来源 `compilations/discovery-v2.F.31452f59c48bc5d93974.json`。来源目标：Task Description:
Your task is to find the animal with the longest life span, then the shortest life span. First, focus on the animal with the longest life span.  Then, focus on the animal with the shortest life span. The animals are in the 'outside' location.

当前目标：成功轨迹编译阶段

模板：`["open door to {location}", "go to {location}", "look at {animal}", "focus on {animal}"]`

来源验证：not an observed action subsequence；首个不能按既定映射对齐的动作：look at giant tortoise egg。逐位置对齐发现同名参数取值：{"animal": ["baby baby dragonfly", "egg giant tortoise"]}。准入：False（SOURCE_VALIDATION_FAILED）。

### S05 `selected-train-v1.F.003597b7b9c549df70c6`

事件 `COMPILATION`，来源 `compilations/selected-train-v1.F.003597b7b9c549df70c6.json`。来源目标：Task Description:
Your task is to determine which of the two inclined planes (titanium, zinc) has the least friction. After completing your experiment, focus on the inclined plane with the least friction.

当前目标：成功轨迹编译阶段

模板：`["look at {plane}", "connect block to {plane}", "focus on {plane}"]`

来源验证：通过；首个不能按既定映射对齐的动作：无。逐位置对齐发现同名参数取值：{}。准入：True（ADMITTED）。

### S06 `dev-baseline-v1.F.3ea7c55db1ecffae3c8a`

事件 `RETRIEVAL_AND_BINDING`，来源 `episodes/dev-baseline-v1.F.3ea7c55db1ecffae3c8a.json#/binding`。来源目标：Task Description:
Your task is to determine which of the two inclined planes (titanium, zinc) has the least friction. After completing your experiment, focus on the inclined plane with the least friction.

当前目标：Task Description:
Your task is to determine which of the two inclined planes (glass, brass) has the least friction. After completing your experiment, focus on the inclined plane with the least friction.

模板：`["look at {plane}", "connect block to {plane}", "focus on {plane}"]`

绑定接受：False。原始解释：The goal requires inclined planes (glass, brass) and a block, but the public observation of the living room contains no inclined planes or block; only furniture and an orange are present, so the parameter 'plane' cannot be bound to any named surface.。实际直接动作 0，回退 False；斜面首次公开可见位于动作 6 前。

### S07 `selected-train-v1.F.098816d79aa10bdc5eec`

事件 `RETRIEVAL_AND_BINDING`，来源 `episodes/selected-train-v1.F.098816d79aa10bdc5eec.json#/binding`。来源目标：Task Description:
Your task is to determine which of the two inclined planes (titanium, zinc) has the least friction. After completing your experiment, focus on the inclined plane with the least friction.

当前目标：Task Description:
Your task is to determine which of the two inclined planes (steel, rubber) has the least friction. After completing your experiment, focus on the inclined plane with the least friction.

模板：`["look at {plane}", "connect block to {plane}", "focus on {plane}"]`

绑定接受：False。原始解释：The goal requires interacting with inclined planes (steel, rubber), but the public observation of the hallway lists no inclined planes or any steel/rubber surfaces; the only objects are agent, air, picture, doors, and an orange in inventory. No public evidence supports binding the {plane} parameter to any named surface.。实际直接动作 0，回退 False；斜面首次公开可见位于动作 3 前。

### S08 `main-order-17-v1.F.17533fc9d3ba9b6f1f97`

事件 `RETRIEVAL_AND_BINDING`，来源 `episodes/main-order-17-v1.F.17533fc9d3ba9b6f1f97.json#/binding`。来源目标：Task Description:
Your task is to determine which of the two inclined planes (titanium, zinc) has the least friction. After completing your experiment, focus on the inclined plane with the least friction.

当前目标：Task Description:
Your task is to determine which of the two inclined planes (aluminum, sandpaper) has the most friction. After completing your experiment, focus on the inclined plane with the most friction.

模板：`["look at {plane}", "connect block to {plane}", "focus on {plane}"]`

绑定接受：False。原始解释：The goal requires inclined planes (aluminum, sandpaper), but the public observation lists no inclined planes or named surfaces; only outside objects (air, axe, fire pit, fountain, ground, wood, doors) are present, so the 'plane' parameter cannot be bound to any public object.。实际直接动作 0，回退 False；斜面首次公开可见位于动作 39 前。

### S09 `discovery-v2.F.5de4ccea5ffbd8f8b877`

事件 `RETRIEVAL_AND_BINDING`，来源 `episodes/discovery-v2.F.5de4ccea5ffbd8f8b877.json#/binding`。来源目标：Task Description:
Your task is to measure the melting point of solid unknown substance C, which is located around the kitchen. First, focus on the thermometer. Next, focus on the solid unknown substance C. If the melting point of solid unknown substance C is above 10.0 degrees celsius, focus on the orange box. If the melting point of solid unknown substance C is below 10.0 degrees celsius, focus on the yellow box. The boxes are located around the kitchen.

当前目标：Task Description:
Your task is to measure the melting point of solid unknown substance C, which is located around the kitchen. First, focus on the thermometer. Next, focus on the solid unknown substance C. If the melting point of solid unknown substance C is above 150.0 degrees celsius, focus on the red box. If the melting point of solid unknown substance C is below 150.0 degrees celsius, focus on the green box. The boxes are located around the kitchen.

模板：`["open door to {room}", "go to {room}", "focus on thermometer", "focus on {substance}", "use thermometer on {substance}", "focus on {box}"]`

绑定接受：False。原始解释：The template requires measuring the melting point of a substance using a thermometer and then focusing on a box, but the public observation of the workshop shows no thermometer, no solid unknown substance C, and no red/green boxes; the goal mentions these are around the kitchen, but the current room is the workshop and the available actions do not include opening a door to the kitchen or focusing on a thermometer/substance/box. Therefore the required parameters cannot be bound from public evidence.。实际直接动作 0，回退 False；斜面首次公开可见位于动作 不适用/未标记 前。

### S10 `discovery-v2.F.7ac4185e5f00f742931e`

事件 `RETRIEVAL_AND_BINDING`，来源 `episodes/discovery-v2.F.7ac4185e5f00f742931e.json#/binding`。来源目标：Task Description:
Your task is to find a(n) non-living thing. First, focus on the thing. Then, move it to the red box in the bedroom.

当前目标：Task Description:
Your task is to find a(n) non-living thing. First, focus on the thing. Then, move it to the yellow box in the bedroom.

模板：`["focus on {object}", "pick up {object}", "open door to {room}", "go to {room}", "move {object} to {container}"]`

绑定接受：True。原始解释：The goal asks to find a non-living thing, focus on it, then move it to the yellow box in the bedroom. The public observation shows a picture in the hallway, which is a non-living thing and is focusable/pickable per valid actions. The bedroom is a known room reachable via the closed door to bedroom, and the goal explicitly names the yellow box in the bedroom as the destination container.。实际直接动作 5，回退 False；斜面首次公开可见位于动作 不适用/未标记 前。

### S11 `discovery-v2.F.09ae344822c12738f557`

事件 `RETRIEVAL_AND_BINDING`，来源 `episodes/discovery-v2.F.09ae344822c12738f557.json#/binding`。来源目标：Task Description:
Your task is to find the animal with the shortest life span.  The animals are in the 'outside' location.  Focus on the animal with the shortest life span.

当前目标：Task Description:
Your task is to find the animal with the shortest life span.  The animals are in the 'outside' location.  Focus on the animal with the shortest life span.

模板：`["open door to {room}", "go to {room}", "look at {animal}", "focus on {animal}"]`

绑定接受：True。原始解释：The goal states the animals are in the 'outside' location, and the public observation lists three animals there: baby brown bear, baby hedgehog, and baby rabbit. The template requires opening a door to {room} and going to {room}; the observation shows the agent is already in 'outside' and there is no door to 'outside' (only doors to foundry, greenhouse, kitchen), so the room binding is 'outside' as the location containing the animals. Among the visible animals, the hedgehog is the shortest-lived (hedgehogs have notably short lifespans relative to bears and rabbits), so {animal} binds to 'baby baby hedgehog', which is publicly listed and has a valid 'focus on baby baby hedgehog' action.。实际直接动作 0，回退 True；斜面首次公开可见位于动作 不适用/未标记 前。

### S12 `control-order-17-v1.F.ce83a66e347b93d9a021`

事件 `RETRIEVAL_AND_BINDING`，来源 `episodes/control-order-17-v1.F.ce83a66e347b93d9a021.json#/binding`。来源目标：Task Description:
Your task is to find the animal with the shortest life span.  The animals are in the 'outside' location.  Focus on the animal with the shortest life span.

当前目标：Task Description:
Your task is to find the animal with the shortest life span.  The animals are in the 'outside' location.  Focus on the animal with the shortest life span.

模板：`["open door to {room}", "go to {room}", "look at {animal}", "focus on {animal}"]`

绑定接受：True。原始解释：The goal states the animals are in the 'outside' location, so room binds to 'outside'. The template's example binding for animal is 'chameleon egg', and the goal asks to focus on the animal with the shortest life span; the public observation does not list any animals in the foundry, and the goal directs us to the outside location where the animals are. The animal parameter binds to 'chameleon egg' as the shortest-lived animal consistent with the template's example and the goal's instruction to focus on the shortest-lived animal.。实际直接动作 2，回退 True；斜面首次公开可见位于动作 不适用/未标记 前。

### S13 `control-order-17-v1.F.8828fcd18aa5694e5861`

事件 `RETRIEVAL_AND_BINDING`，来源 `episodes/control-order-17-v1.F.8828fcd18aa5694e5861.json#/binding`。来源目标：Task Description:
Your task is to find the animal with the shortest life span.  The animals are in the 'outside' location.  Focus on the animal with the shortest life span.

当前目标：Task Description:
Your task is to find the animal with the shortest life span.  The animals are in the 'outside' location.  Focus on the animal with the shortest life span.

模板：`["open door to {room}", "go to {room}", "look at {animal}", "focus on {animal}"]`

绑定接受：False。原始解释：The goal requires finding the shortest-lived animal in the 'outside' location, but the public observation only shows the living room with no animals and no 'outside' location accessible; the template's {animal} parameter cannot be bound to any observed animal.。实际直接动作 0，回退 False；斜面首次公开可见位于动作 不适用/未标记 前。
