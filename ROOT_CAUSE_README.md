# FlowEvo–ScienceWorld 阶段 A：零 API 根因审计

从历史提交 `a0f6e0816c23a4abcb646a5fb018e786c2a6be95` 创建，保留旧实验全部内容；原运行时、模型配置和历史统计不变。

- [完整中文报告](reports/ROOT_CAUSE_AUDIT_ZH.md)
- [成功技能完整链路及13个环节案例](reports/SKILL_REUSE_BOTTLENECK_ZH.md)（12条独立轨迹）
- [可复算步骤](reports/ROOT_CAUSE_REPRODUCE.md)
- [可证伪的下一轮决策](reports/NEXT_RESEARCH_DECISION_ZH.md)
- [输入与零 API 核验回执](artifacts/root_cause_run_receipt.json)

分析252条历史轨迹、7453个动作，主要基线116条单列。18组局部动作对照/36条免费JVM分支只使用14条TRAIN/DEV轨迹；另有6个治理记账夹具。它们不是新模型成绩。

**本轮新增 DeepSeek 调用0次，新增API费用0元。当前证据不足以支持提出新的FlowEvo扩展算法。**

不要执行旧复算文档中的付费调度命令；真实JVM诊断使用断网命名空间，只开放本机JVM通信；另有公开记录的纯静态复算。阶段B未执行，也未获授权。
