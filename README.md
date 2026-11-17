# FlowEvo–ScienceWorld 失败对比状态约束实验

已完成真实服务器运行与 DeepSeek 实验。主 TEST 120 局、范围外对照 20 局，全部完成，无缺失。主要 F-I 为 11/24，完整 F 为 9/24，差 +8.33 个百分点，分层 bootstrap 95% 区间 [-12.50, +25.00]。F-I 与 F-T 持平、低于 F-S 的 13/24，且有 3 局持续否决停止。这是两个任务家族的小样本 pilot，不能确立普遍优势。全流程峰值价估算 $12.375241，包含废弃运行和开发成本。

- [中文最终报告](reports/FINAL_REPORT_ZH.md)
- [真实测试过的安装、离线复算和模型实验命令](REPRODUCE.md)
- [适配与原生能力映射](reports/FLOWEVO_SCIENCEWORLD_ADAPTATION.md)
- [环境、评分和信息边界](reports/ENVIRONMENT_AND_SCORING_AUDIT.md)
- [基线与失败机会审计](reports/BASELINE_AND_FAILURE_AUDIT.md)
- [约束学习及负面工程证据](reports/CONSTRAINT_LEARNING_REPORT.md)
- [逐任务结果](results/episodes.csv)、[冻结主统计](results/summary.json)、[费用账本](results/costs.csv)
- [冻结协议](artifacts/protocol.json)、[可复现 YAML](configs/experiment_plan.yaml)、[上游许可](UPSTREAM_LICENSES.md)

运行 `bash output/scripts/bootstrap.sh <工作根目录>` 安装时，仓库应位于工作根目录的 `output/`；上游位于 `vendor/`，私有账本和凭据分别在 `runs-private/`、`secrets/`，均在 Git 仓库外。详见复现说明。

`results/*sanitized.jsonl.zst` 包含自有完整公开轨迹、原始模型请求/响应及学习治理审计；无密钥即可恢复并复算。已公开 TEST 视为暴露，未使用 TEST 清单不发布。原始私有日志保留服务器，未把上游无统一许可证仓库或大体积 JAR 复制进本项目。

所有主组保留成功编译、检索、直接执行、引导、回退和治理。模型只能使用公开观察、完整合法动作接口与普通环境反馈；禁止 Gold、专家路径和隐藏评分驱动重试。规则最多一次重新规划，无持续找题、无限修订或选择性重跑。
