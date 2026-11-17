# 零API工程阶段复算

本分支从 `af07480e7639a583293d825baddc8213d6dfddf8` 出发；历史发布器从 `a0f6e0816c23a4abcb646a5fb018e786c2a6be95` Git对象提取。沿用requirements.lock.txt及upstream_manifest.json中的固定依赖。无需API Key，不读取api.txt，不启动请求调度器。

## 目录与输入

独立根目录内仓库名为output，input-snapshot指向上一阶段已验证的只读副本，vendor指向固定上游源码。正式运行使用 `/root/flowevo-engineering`；原实验及上阶段目录保持不变。

没有原始副本时，在全新独立目录使用原有restore_public_run.py恢复公开记录，再使用root_cause_prepare_inputs.py制作独立快照。两者拒绝覆盖已有输入。准备器会为本次恢复重新生成root_cause_input_manifest.json，并把仓库自带清单另存为.published.json；不要把复算导致的这项历史清单字节差异作为新实验提交。公开恢复的费用浮点尾差容许范围与上一阶段相同，绝不计为新增费用。

## 执行

```bash
cd /root/flowevo-engineering/output
# 使用已经安装固定依赖的环境；PYTHONPATH使新分支代码优先于旧可编辑安装。
export PYTHONPATH="$PWD/src:/root/flowevo-scienceworld/vendor/FlowEvo/src"
export PYTHON=/root/flowevo-scienceworld/.venv/bin/python
unshare -n -- bash
ip link set lo up
export FLOWEVO_OFFLINE_ONLY=1
unset DEEPSEEK_API_KEY OPENAI_API_KEY
$PYTHON scripts/run_engineering_offline.py --root ..
$PYTHON scripts/engineering_reports.py --root ..
$PYTHON scripts/engineering_verify.py --root .. \
 --original /root/flowevo-scienceworld/runs-private
```

在其它机器可省略最后的--original，只核验本地快照。正式运行中提供该参数，另核对原服务器记录哈希。需要Linux网络命名空间权限；不支持时应提供等价外网隔离，不应静默省略网络边界。FLOWEVO_OFFLINE_ONLY阻止DeepSeek客户端构造和请求，即使客户端在设置开关前已构造也不能发送新call。

configs/engineering_zero_api.yaml声明零请求/零费用、3个并行静态作业和4个JVM工作进程。入口先运行测试，再并行执行治理重算、动作审查、表示/绑定检查，最后运行真实JVM检查。每个脚本均可单独复算；它们只读取保存输出，没有模型决策续跑。

## 输出及解释限制

- governance_events.csv、governance_template_deltas.csv、governance_summary.csv：固定历史观察下三种记账重算。库发生分歧后不假定旧模型响应代表新策略。
- action_response_audit.csv：全部7691条保存action响应，含253条未执行提议；候选警告、正常措辞与未知分开。不是独立准确率测试。
- skill_representation_audit.csv：34个缓存编译输出的真实来源验证及唯一参数对齐；不重新生成技能。
- conditional_binding.csv：TRAIN/DEV固定公开状态上的候选验证。binding_plan_v2.json是最终计划；binding_plan.json是可变对象别名问题修复前的废弃探查计划，保留以说明过程，不参与最终统计。
- jvm_receipts.json：12个只报警执行一致性检查及2个去重准备片段。没有新的完整技能迁移或任务成功率。
- verification.json：原始哈希、账本、隔离、测试及源代码摘要。

诊断条件绑定接口位于conditional_binding.py；只在所有当前可证明条件通过时返回ALLOW。它没有替换线上模型绑定，也不会自动将修正候选入库。未知生物类别、目标比较、后续房间状态或不支持的自然语言条件均不能以普通valid-action列表代替证明。

发布前运行已有root_cause_scan_publication.py，仅扫描凭据模式，不读取真实密钥。CSV保留原始公开文本的换行和空白，因此源码空白检查应排除CSV内容；不能为消除空白提示而改写原观察。
