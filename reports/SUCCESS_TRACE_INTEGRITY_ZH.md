# FlowEvo 成功轨迹的过程完整性审计

## 结论与范围

现有主要 TRAIN/DEV 的31个独立成功 task/variation 中，2条具有完整公开过程支持，17条最终选择缺少足够的公开依据，另有2条部分支持、10条不需要复杂实验。对19条需要比较或阈值判断的轨迹，18条缺少充分的观测决策依据。这里的“缺少”描述日志中的证据，不能推出随机猜测，也不能推出所有成功都不可学习。

其中完整过程是温度测量与融冰。温度的“读数→阈值→盒子”关系仍保存在编译后的 L2 规则；L1 缺少运行中按读数重新选择目标的结构，并遗漏末次必要的 focus。因此证据更支持先核查成功数据的过程含量，并做针对性的表示修复；尚不足以把总体问题归结为编译器抹掉了多数完整科学方法。

父提交为 `5ae0dcdf80bf81c4f5acd34d24f75501ddda942b`。本阶段新增实验模型请求0次、新增API费用0、新JVM回放0、新TEST求解0，没有重报任务成功率。运行时代码、治理、检索、直接执行、引导和回退均未改动。这里的0调用指实验 provider 请求；两次助手审阅不被包装成两名人类专家审阅。

## 样本与独立审阅

共建立102条历史成功记录的关联库存：31条主集、8条补充版本/重复运行、63条仅作元数据描述的TEST记录。主集为 F 组 discovery-v2、selected-train-v1、dev-baseline-v1，31条恰为31个不同task/variation。8条补充中只有3个主集之外的新单元，另5条是主集单元的版本重复，不能增加主统计权重。旧主基线42条成功包括31条TRAIN/DEV和11条F组TEST，不与102条跨组/版本库存混用。

所有39条TRAIN/DEV成功记录都有公开轨迹、保存的编译请求及响应；37条有独立编译结果文件，2条仅恢复请求响应。历史环境成功由原记录三处相符字段确认，只用于纳入库存，不作为选择哪个对象的依据。公开反馈、look、inventory仍用于过程审阅，隐藏判分、正确答案与专家路径未进入绑定或变体设计。

先生成仅有原始公开目标、状态、动作、反馈和saved reason的源包，再逐条审阅；编译字段不进入源包。两份助手审阅均覆盖39条，38条标签一致。主审已有项目背景，第二审阅分支在源审阅时只读源包；这不是严格盲态的两人专家一致性实验。熔点110的唯一分歧从“选择无依据”裁为“部分支持”：有一次当前温度测量，但没有测到熔点，双方均认为选择没有充分依据。冻结后才连接编译文件，原标签、分歧和哈希均保留。

`INSUFFICIENT_EVIDENCE`指日志缺失到无法判定；当前完整日志没有观察到所需物理证据，通常属于`ANSWER_WITHOUT_OBSERVED_SUPPORT`，二者不混淆。角色和适用条件的语义审阅另由第二审阅完成，主审复核关键案例，未宣称其经过两份独立编译标注。

| 源标签 | 主集数量（分母31） |
| --- | ---: |
| PROCESS_SUPPORTED | 2 |
| PARTIALLY_SUPPORTED | 2 |
| ANSWER_WITHOUT_OBSERVED_SUPPORT | 17 |
| PROCESS_NOT_REQUIRED | 10 |
| INSUFFICIENT_EVIDENCE | 0 |

## 六项指标

以下是固定成功语料的描述性全量审计，非随机抽样推断；不给误导性的总体置信区间，也不计算新的任务成功率。

| 指标 | 结果与分母 | 解释 |
| --- | --- | --- |
| 有完整过程支持 | 2/31（6.5%）；复杂推断/实验任务内2/20（10.0%） | 10条简单类别任务和1条活物状态异常单列 |
| 缺关键决策依据 | 比较/阈值任务18/19（94.7%）；全主集18/31（58.1%） | 17条无充分依据＋熔点部分支持；不等于随机猜中 |
| 关键步骤保留 | 实验核心2/2；包括必要完成标记1/2 | 温度测量和放盒保留，末次focus缺失；融冰核心保留 |
| 参数角色与条件联合支持 | 6/31有支持，4/31有明确缺陷，21/31不确定 | 角色7真/3假/21未知；条件29真/1假/1未知；不是31条的失败率 |
| 观测—决策依赖保留 | 来源确有此关系的1条中，L1可执行分支0/1；raw/L2规则文本1/1 | 分母只有温度例，不能推广为整个编译器“全部丢失” |
| 可信完整迁移候选 | 1个保留方法的结构候选（融冰）；完整迁移已验证0个 | 12个静态条件检查未放行完整序列，未做真实迁移求解 |

条件“支持”仅指原applicability描述与来源事实相容，不表示足以覆盖所有未来世界状态；参数角色“支持”要求可辨别的来源对象/房间角色与确定对齐，别名或多重对齐保守记未知。温度盒子参量独立与观测决定盒子的关系是两个维度，前者支持不挽救后者。

## 逐类证据

### 温度：观察确实解释了选择

`discovery-v2.F.2beaa66b5bcd3db3dc64`，use-thermometer:151。目标明确高于0°C用蓝盒、低于0°C用橙盒。第9步测得−13°C；第10步reason使用小于0的判断，第14步放入橙盒，第15步查看确认，第17步focus物质完成。测量与动作之间有公开可核查关系。reason不是测量的替代品，测量来自环境反馈。

### 融冰：有可见的状态变化

`discovery-v2.F.6aebd9fb1322c1074fb6`，melt:4。第5步开冰箱、第6步有效focus冰、第7步拾取、第8步放炉上、第9步启动炉子；第9步公开look由ice变为water。第3步无效focus不是必要步骤，编译删除它不构成信息损失。补充版本的棉花糖任务也有热源、放置及第11步wait后液态反馈，但它不增加主集分子。

### 斜面：10条来源均未观察到充分的摩擦比较

在10条主集摩擦任务中，look给出名称/表面信息，connect的实际反馈是端子连接，focus承担选择而非摩擦测量。不能把存在这些接口动作当作已进行了科学比较。例如钛/锌 `selected-train-v1.F.003597b7b9c549df70c6` 第1/2步观察两面，第3/4步连接，第5步focus钛，没有滑动时间或比较反馈。匿名面 `discovery-v2.F.9cef108e88fa0d6aff89` 也没有可解释选择的测量。材料常识可能影响模型判断，但日志没有证明它可靠地区分了当题物理结果。

### 寿命：5条缺少公开寿命排序；知识先验不能被当作已测量

可见内容为物种名和生命阶段，没有寿命数值或可核查排序。有些reason使用刺猬较短、龟较长等先验，有些将focus误作查看。严格公开证据口径下标记无充分依据；不声称知识类问题一律必须现场测量，也不把“未记录依据”改写为“随便猜”。两条先最长后最短的源轨迹有双选择顺序，虽无验证排序，顺序本身仍可审查编译保真。

### 遗传：2条没有公开的杂交/后代证据

`discovery-v2.F.5338a5b7b1763d020e75`与`discovery-v2.F.ae8d0d5850873ad49924`只观察种子、容器并拾取/选择，没有种植、杂交或后代性状比较。最终颜色盒选择的科学依据未在来源中出现，因此缺失遗传推断不能归因于编译删除。

### 熔点：当前温度不是熔点

`discovery-v2.F.3fbe681bf784f2d76d21`，measure-melting-point-unknown-substance:110。第5步测得固体当前10°C；没有加热、熔化或相变平台。第6步reason从“等于10、既不大于也不小于”转成选择橙盒，不能建立目标要求的熔点分支。裁定部分支持，最终决策不支持；环境原成功字段保持原样。

### 简单类别与状态异常

10条找非生物/植物/动物的任务按类别搬运，不强求实验比较，标为PROCESS_NOT_REQUIRED。这不保证路径高效或状态持续有效：蜂可逃逸，源轨迹也多次检查和重新拾取。例如`dev-baseline-v1.F.cfcb5065ead3594fa047`第75步放蜂、第76步查看、第77步focus；另一些任务最终公开盒内容为空，须保留这个状态现象而不重写历史成功。其L2仍包含重取策略，不能概括为完全丢掉状态反馈。

活物 `discovery-v2.F.b305a2703799b76c3a98` 初始正确识别adult pea plant，但第6步已经dead，第7步实际搬运dead pea plant；这是部分支持的持续状态问题，不能归入复杂科学比较失败。它与任务只要求plant的另一个样本不同。

## 四类归因与研究判断

| 类别 | 主集数量 | 本次解释 |
| --- | ---: | --- |
| A 来源过程完整、关键方法保留 | 1 | 融冰，结构候选，未证明迁移 |
| B 来源过程完整、某层关键结构缺失 | 1 | 温度，L1分支/末focus缺失，L2阈值规则仍在 |
| C 成功但关键决策依据不足 | 18 | 17条无充分依据＋熔点部分支持；仍可能同时有可辨认的角色/步骤缺陷 |
| D 简单或部分状态案例 | 11 | 10条简单＋活物状态异常；不强行称为算法失败 |

当前证据首先质疑“环境成功即可作为完整可迁移方法来源”的充分性。它没有证明采用新的过程技能算法优于保留适用条件、分离角色、补足必要标记等简单修正。先以源过程证据做质量审查，保留L2已有规则，修复可定位的状态/角色与完成标记问题，再对融冰及温度做不收费的验证，具有更明确的依据。仍不建议据此宣称失败学习或新编译算法有效，也不自动启动付费验证。

## 主集逐条索引

步骤编号从1开始；详细measurement/comparison/selection索引、源文件字节/语义哈希、原服务器哈希及生命周期见[来源CSV](../results/success_trace_audit.csv)。完整公开轨迹可用复算脚本恢复，可读源包位于[源包目录](../artifacts/success_audit/source_packets)。

| 轨迹ID | 独立单元 | 源标签 | 最终选择相关步骤 |
| --- | --- | --- | --- |
| `dev-baseline-v1.F.3ea7c55db1ecffae3c8a` | inclined-plane-friction-named-surfaces:1011 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [7] |
| `dev-baseline-v1.F.722d467db63128d43cf2` | inclined-plane-friction-named-surfaces:989 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [16] |
| `dev-baseline-v1.F.77525ad34ec157f0577b` | inclined-plane-friction-named-surfaces:754 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [19] |
| `dev-baseline-v1.F.cfcb5065ead3594fa047` | find-animal:162 | PROCESS_NOT_REQUIRED | [2, 75, 77] |
| `discovery-v2.F.09ae344822c12738f557` | lifespan-shortest-lived:16 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [4] |
| `discovery-v2.F.2beaa66b5bcd3db3dc64` | use-thermometer:151 | PROCESS_SUPPORTED | [14, 17] |
| `discovery-v2.F.2dcdca293d9b16367852` | lifespan-longest-lived:22 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [8] |
| `discovery-v2.F.31452f59c48bc5d93974` | lifespan-longest-lived-then-shortest-lived:6 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [6, 7] |
| `discovery-v2.F.3fbe681bf784f2d76d21` | measure-melting-point-unknown-substance:110 | PARTIALLY_SUPPORTED | [6] |
| `discovery-v2.F.5338a5b7b1763d020e75` | mendelian-genetics-known-plant:20 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [31] |
| `discovery-v2.F.5bfedeb6e825464e626d` | inclined-plane-friction-named-surfaces:281 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [13] |
| `discovery-v2.F.6aebd9fb1322c1074fb6` | melt:4 | PROCESS_SUPPORTED | [6] |
| `discovery-v2.F.7ac4185e5f00f742931e` | find-non-living-thing:142 | PROCESS_NOT_REQUIRED | [1, 5] |
| `discovery-v2.F.8a0e00d29345445b21a5` | lifespan-longest-lived-then-shortest-lived:56 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [6, 7] |
| `discovery-v2.F.8c8a122797c51e4659c6` | lifespan-shortest-lived:51 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [8] |
| `discovery-v2.F.965d4f1df81ea937ed3b` | find-plant:59 | PROCESS_NOT_REQUIRED | [12, 14] |
| `discovery-v2.F.9cef108e88fa0d6aff89` | inclined-plane-friction-unnamed-surfaces:32 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [8] |
| `discovery-v2.F.ae8d0d5850873ad49924` | mendelian-genetics-known-plant:3 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [10] |
| `discovery-v2.F.b305a2703799b76c3a98` | find-living-thing:19 | PARTIALLY_SUPPORTED | [1, 7] |
| `discovery-v2.F.d9797b94d94a3a12ea4b` | find-non-living-thing:18 | PROCESS_NOT_REQUIRED | [1, 5] |
| `discovery-v2.F.def63cb9dcbcef266a65` | find-animal:94 | PROCESS_NOT_REQUIRED | [2, 11] |
| `selected-train-v1.F.003597b7b9c549df70c6` | inclined-plane-friction-named-surfaces:423 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [5] |
| `selected-train-v1.F.098816d79aa10bdc5eec` | inclined-plane-friction-named-surfaces:269 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [5] |
| `selected-train-v1.F.1421639dc7e19fcaab35` | inclined-plane-friction-named-surfaces:25 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [8] |
| `selected-train-v1.F.17c9fd4a9e6176a23caf` | inclined-plane-friction-named-surfaces:341 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [10] |
| `selected-train-v1.F.34085a7755ec1e593502` | find-animal:120 | PROCESS_NOT_REQUIRED | [2, 56] |
| `selected-train-v1.F.47673143391e75c3cf13` | find-animal:27 | PROCESS_NOT_REQUIRED | [49, 53] |
| `selected-train-v1.F.68edb4b7a582dbbbf477` | find-animal:73 | PROCESS_NOT_REQUIRED | [16, 18] |
| `selected-train-v1.F.7d7a4efdcc6531231f85` | find-animal:87 | PROCESS_NOT_REQUIRED | [10, 16, 18, 64, 68] |
| `selected-train-v1.F.8658e75cca5cffee5b04` | inclined-plane-friction-named-surfaces:472 | ANSWER_WITHOUT_OBSERVED_SUPPORT | [19] |
| `selected-train-v1.F.ddde1cdd88f20265f732` | find-animal:74 | PROCESS_NOT_REQUIRED | [35, 81, 84] |

## 补充版本，独立于主统计

| 轨迹ID | 单元 | 源标签 |
| --- | --- | --- |
| `batch-sensitivity-1-v1.F.1421639dc7e19fcaab35` | inclined-plane-friction-named-surfaces:25 | ANSWER_WITHOUT_OBSERVED_SUPPORT |
| `batch-sensitivity-8-v1.F.1421639dc7e19fcaab35` | inclined-plane-friction-named-surfaces:25 | ANSWER_WITHOUT_OBSERVED_SUPPORT |
| `batch-sensitivity-8-v1.F.ddde1cdd88f20265f732` | find-animal:74 | PROCESS_NOT_REQUIRED |
| `discovery-v1.F.1b4703786cd7f2ff0592` | find-animal:42 | PROCESS_NOT_REQUIRED |
| `discovery-v1.F.279ad8d80a9088c7546b` | change-the-state-of-matter-of:12 | PROCESS_SUPPORTED |
| `discovery-v1.F.965d4f1df81ea937ed3b` | find-plant:59 | PROCESS_NOT_REQUIRED |
| `discovery-v1.F.d9797b94d94a3a12ea4b` | find-non-living-thing:18 | PROCESS_NOT_REQUIRED |
| `discovery-v1.F.e1913f9868b6d9fe9f61` | inclined-plane-determine-angle:23 | ANSWER_WITHOUT_OBSERVED_SUPPORT |

## 复核材料

[信息损失报告](COMPILATION_INFORMATION_LOSS_ZH.md)、[矩阵CSV](../results/skill_information_loss.csv)、[复算说明](SUCCESS_AUDIT_REPRODUCE.md)、[审阅冻结](../artifacts/success_audit/source_review_freeze.json)、[分歧记录](../artifacts/success_audit/review_disagreements.json)、[机器统计](../artifacts/success_audit/summary.json)和[执行核验](../artifacts/success_audit/verification.json)共同构成证据链。历史TEST只保留索引及既有元数据，本次没有增加TEST过程标签或成绩表。
