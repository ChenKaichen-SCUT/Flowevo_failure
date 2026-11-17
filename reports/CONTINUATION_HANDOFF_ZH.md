# 下次继续工作的交接记录

## 已完成到哪里

1. 原始真实DeepSeek/ScienceWorld实验：`a0f6e0816c23a4abcb646a5fb018e786c2a6be95`，分支 `feat/scienceworld-failure-invariants`。原始请求账本8941次，历史估算费用USD12.375240828。
2. 零API根因诊断：`af07480e7639a583293d825baddc8213d6dfddf8`，分支 `feat/scienceworld-root-cause-audit`。
3. 零API工程修复与机制证伪：`5ae0dcdf80bf81c4f5acd34d24f75501ddda942b`，分支 `feat/scienceworld-engineering-falsification`。直接/引导/仅检索信用分离；动作一致性检查只报警；保留适用条件、角色与来源契约，条件绑定保持保守安全验证。
4. 零API成功轨迹与编译信息保真审计：GitHub `0ec09d1f43714066b76489be73be9e9cdde3d88e`，分支 `feat/scienceworld-success-trace-audit`。最新运行时代码仍是工程修复阶段版本，此阶段只增加审计。
5. 当前服务器退役备份：分支 `backup/server-retirement-20261117`；完整加密文件在Release `server-backup-20261117`。恢复步骤见[服务器恢复说明](SERVER_RESTORE_ZH.md)。

服务器成功审计目录中的Git HEAD `600cd248fb3a6c4b9c4288d74ddf9d860e82e0b6` 与GitHub `0ec09d1` 的工作树内容相同；最后换行字节保留通过连接器提交，作者/时间导致提交ID不同。建议从GitHub备份分支另建工作分支，旧Git快照仅保留历史。

## 最新可信结论

主统计31个独立TRAIN/DEV成功单元：完整过程支持2、部分支持2、选择依据不足17、简单任务10。19条比较/阈值任务中18条缺少充分公开决策依据，不等于证明随机猜测。

39条TRAIN/DEV来源审阅在连接编译文件前冻结，两份助手审阅38条标签一致。37条有独立编译文件，另外2条只恢复到原始响应。全部公开步骤进入编译输入；reason未传入。来源有效L1为主集13/31，不能解释为13个完整迁移技能。

温度测量的阈值关系仍在L2；L1缺少新读数驱动的重新绑定并遗漏末次必要focus。融冰保留关键方法，是1个结构候选，完整迁移尚未证明。当前证据不足以直接支持提出新算法。12项静态检查未放行完整模板，不是任务执行失败率。

## 继续时保持的边界

- 当前研究阶段仍是零新增模型API调用。恢复程序不会启动模型或重跑实验；下一阶段若要付费，先由用户明确授权范围与预算。
- 保留FlowEvo成功编译、检索、直接执行、引导、动态回退和治理，不人为削弱基线。
- 禁止正确答案、专家路径或隐藏评分驱动重试；正常公开环境反馈可以使用。上游快照中的Gold文件仅属原始软件备份，不是允许读取来选动作的证据。
- 已公开TEST仅作历史记录，不用于新技能设计、调参或当作未见测试。主统计按task/variation，不把版本重复算成独立证据。
- 不将“源轨迹没有的信息”说成“编译器丢掉的信息”；分开L1可执行结构、L2文本、原始输入和序列化层。
- 不重写历史任务成功结果。若无收益、简单规则持平或缺少状态失效机制，照实报告。

## 推荐先读

[成功轨迹审计](SUCCESS_TRACE_INTEGRITY_ZH.md)、[编译信息损失](COMPILATION_INFORMATION_LOSS_ZH.md)、[审计复算](SUCCESS_AUDIT_REPRODUCE.md)。逐条数据是 `results/success_trace_audit.csv`、`results/skill_information_loss.csv`。原始私人文件须用密钥解密，公开离线审计可直接用仓库脱敏归档恢复。

固定上游：FlowEvo `36e81efd4d1fdbabca7366200b15808ebef157fa`；ScienceWorld `e8216d6044e8e39be9fcb185e3b2dfb602584b52`；failure-experiments `fde8da720f09ae823cd36c4582a9413e764ab74a`。快照保留源码、Git对象、JAR及安装环境，不需要旧服务器存活。
