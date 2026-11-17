# 技能表示与条件绑定：简单修正的边界

覆盖全部96条正式基线TRAIN/DEV历史轨迹（含8条重复TRAIN敏感性，不能算新独立任务）。其中34个已保存编译输出通过当前真实ScienceCompiler的缓存路径重新做来源验证，**没有向模型重新生成技能**。13个原候选通过来源验证；21个不通过。只在来源动作的参数对齐唯一时拆分同名参数，得到5个严格来源有效的修正候选；15个多重对齐和1个无法对齐保留拒绝。不能把不同字符串自动当不同对象，尤其可能存在别名。

|来源|任务|原→修正来源有效|修正细节|
|---|---|---|---|
|batch-sensitivity-8-v1.F.1421639dc7e19fcaab35|inclined-plane-friction-named-surfaces|False→True|{"aligned_source_indices": [1, 2, 4, 7, 8], "split_parameters": {}, "status": "SOURCE_VALID_CANDIDATE", "transfer_verified": false}|
|discovery-v2.F.2dcdca293d9b16367852|lifespan-longest-lived|False→True|{"aligned_source_indices": [0, 1, 2, 3, 4, 5, 6, 7], "split_parameters": {"animal": ["giant tortoise egg", "egg giant tortoise"], "door": ["door to hallway", "door to greenhouse", "door to outside"], "room": ["hallway", "greenhouse", "outside"]}, "status": "SOURCE_VALID_CANDIDATE", "transfer_verified": false}|
|discovery-v2.F.b305a2703799b76c3a98|find-living-thing|False→True|{"aligned_source_indices": [0, 1, 2, 3, 4, 5, 6], "split_parameters": {"living_thing": ["adult pea plant", "dead pea plant"]}, "status": "SOURCE_VALID_CANDIDATE", "transfer_verified": false}|
|discovery-v2.F.def63cb9dcbcef266a65|find-animal|False→True|{"aligned_source_indices": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "split_parameters": {"destination": ["kitchen", "yellow box"], "door": ["door to hallway", "door to kitchen"], "room": ["hallway", "kitchen"]}, "status": "SOURCE_VALID_CANDIDATE", "transfer_verified": false}|
|selected-train-v1.F.1421639dc7e19fcaab35|inclined-plane-friction-named-surfaces|False→True|{"aligned_source_indices": [1, 2, 3, 4, 5, 6, 7], "split_parameters": {"room": ["hallway", "workshop"]}, "status": "SOURCE_VALID_CANDIDATE", "transfer_verified": false}|

编译器生成的applicability原文保留在ScienceSkillTemplate，穿过入库、序列化、加载和检索；同时单列房间/导航、实验对象、仪器、搬运目标和最终选择角色。6个M0模板从保存编译输出恢复条件，原动作、效用、准入和状态不变。5个修正候选没有自动入库。

## 条件绑定检查

在15条实际检索过模板的TRAIN/DEV轨迹上，预先选初始状态和第一次公开出现斜面的状态。枚举公开候选，不按宿主得分选赢家。最终共975个映射/表示检查，**不是975条任务**；其中完整模板489个、准备片段486个。

条件验证器为三值逻辑：FALSE拒绝、UNKNOWN弃权，只有全部有公开证据才ALLOW。当前只覆盖有界条件语法；其它原文条件完整保留但不默认为真。类别和目的地内容未被证实时仍未知。即使接口允许connect agent/air/wire，也不证明这些实体能替代源实验对象；参数化一个字面量不等于证明角色可交换。

|判定|候选数|
|---|---|
|ABSTAIN_INSUFFICIENT_EVIDENCE|119|
|ALLOW|4|
|REJECT_CONDITION_FALSE|852|

完整模板ALLOW数为0。准备片段ALLOW数为4，去重后仅2个真实JVM分支、同一DEV公开状态。它们可以分别观察并连接两块斜面；环境反馈仍是terminal连接，未给出摩擦比较结论。最终focus选择被明确保留为未知，未执行目标选择。**这只恢复了局部可执行性，没有恢复完整技能迁移，也没有证明实验科学性。**

该验证器是可调用的离线诊断接口，没有接管线上bind_skill或通过全面拒绝来重做基线。原因是条件解析覆盖和实验结果解释尚未得到充分验证。原模型绑定会收到新增保留的条件，但本轮没有调用它，不能声称新的自然绑定行为改善。当前源验证和每步valid-action守卫均未放宽。

## 工程过程与可证伪边界

首次结构探查发现底层to_dict返回可变列表，诊断参数提升会误改原模板对象；现已使用独立深拷贝并增加隔离回归测试。binding_plan.json保留为已废弃的探查计划；最终使用binding_plan_v2.json，全部候选重新计算。没有据得分挑映射、删除负例或继续尝试目标答案。

可推翻“这些简单修正已足够”的证据已存在：完整技能仍缺可证明的目标选择；许多来源对齐仍不唯一。但不能反过来声称新算法必要，因为大部分自然语言条件仍不能被第一版验证器完整解释。下一步仍可免费扩充条件覆盖、审查角色约束和科学测量契约；现有数据不足以证明它们能解决大部分任务问题。
