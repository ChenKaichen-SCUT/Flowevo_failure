# 阶段 A 零 API 复算

本分支从历史 `a0f6e0816c23a4abcb646a5fb018e786c2a6be95` 创建；历史模型、配置、运行记录、评分和统计脚本不变。新增脚本只处理日志或本地 JVM。不要执行历史 REPRODUCE.md 中的模型调度/训练命令。本轮未读取 api.txt，发布也不使用要求读取密钥的历史 scan_publication.py。

CSV 是按任务书要求提供的科研审计数据库，使用现有 Python CSV/JSON 工具，不另生成 XLSX 工作簿。来源值、机器筛查标签与因果解释分列；UNKNOWN不替换为0或确定诊断。

## 输入

在独立工作根目录中，仓库命名为 `output`。复用已验证的固定依赖环境，或仅运行历史 `bootstrap.sh` 安装（它不调用模型）。优先将原 `runs-private` 中 episodes、compilations、banks、diagnoses、probes、dev_local、requests、根目录JSON、resource_samples.jsonl复制到 `input-snapshot`；通过 SQLite 只读连接的 backup 取得账本副本。不复制 secrets、供应商网页、未来TEST清单。输入 SHA 记录在 root_cause_input_manifest.json，副本移除写权限。

没有私有日志时，先在全新目录使用已有 `restore_public_run.py` 恢复公开压缩记录，再用下面的准备脚本复制。该还原器和准备脚本均拒绝覆盖现存输入目录；勿用强制覆盖。还原时JSON排版可能不同，当前快照SHA重新生成，已发布清单另存为 `.published.json`，但原CSV/统计应相同。公开原始SHA映射仍在 export_mapping.json。

```bash
# 在 output 目录；仅在没有原日志且独立根目录没有 runs-private 时执行此行：
$PYTHON scripts/restore_public_run.py --root ..
# --source 可改为原服务器 runs-private 的绝对路径。拒绝现存 input-snapshot。
$PYTHON scripts/root_cause_prepare_inputs.py --root .. --source ../runs-private
```

准备脚本按完成的历史run名称和记录目录白名单复制，不读取任何凭据。新清单记录SQLite只读备份、SHA和历史请求合计；其文件数量会随原/公开来源是否含prefix文件及旧扫描回执而不同，不强行伪装与原私有文件字节相同。

本次服务器分析直接采用原始副本，18794个清单文件。原始目录与副本最终均核对哈希未变。另从公开记录恢复并独立复制18538个文件，得到相同核心汇总和技能链路CSV，回执见 root_cause_public_reproduction.json；两份清单分别保存为 root_cause_input_manifest.json 和 root_cause_public_input_manifest.json。

## 复算命令

以下全部在 Linux 独立网络命名空间执行，仅启用loopback让Py4J访问JVM。无需任何API Key或调度器。在有权限创建namespace的环境执行；若无权限，应配置等价外网禁止措施，不能静默去掉隔离后启动模型服务。

```bash
cd <独立工作根目录>/output
mkdir -p ../recompute/output/results ../recompute/output/artifacts
ln -s "$(realpath ../input-snapshot)" ../recompute/runs-private
cp artifacts/protocol.json ../recompute/output/artifacts/
unshare -n -- bash
ip link set lo up
unset DEEPSEEK_API_KEY OPENAI_API_KEY
# PYTHON 指向已安装 requirements.lock.txt 与固定上游的 Python。
PYTHON=/root/flowevo-scienceworld/.venv/bin/python
$PYTHON scripts/analyze_results.py --root ../recompute --runs \
 discovery-v2 selected-train-v1 dev-baseline-v1 \
 batch-sensitivity-1-v1 batch-sensitivity-8-v1 \
 main-order-17-v1 main-order-29-v1 control-order-17-v1
$PYTHON scripts/summarize_audit.py --root ../recompute
$PYTHON scripts/verify_reproduction.py --root ../recompute --run-id discovery-v2
$PYTHON scripts/root_cause_audit.py --root ..
$PYTHON scripts/root_cause_counterfactuals.py --root .. --workers 4
$PYTHON scripts/root_cause_verify.py --root ..
$PYTHON scripts/root_cause_reports.py --root ..
```

有服务器原目录时，最后可传 `--original /root/flowevo-scienceworld/runs-private`，额外验证原始记录未改以及账本仍为8941次历史调用。不要在已有快照上重新运行恢复器。

所有新增CSV使用UTF-8/LF，行内JSON保存证据原文；禁止按Excel公式执行轨迹文字。报告由固定脚本重建。主要基线116条与其它组分层，先前18个局部检查均不含TEST。最早动作分歧是查阅入口，仍需结合目标、初始房间和公开反馈解释，不能把首个字符串差异当根因。

## 检验口径

本次服务器原副本复算的三个旧统计文件逐字节一致。另行从公开压缩记录恢复时，episodes.csv、costs.csv仍逐字节一致；summary.json只有历史费用浮点求和从12.375240827999969变为12.375240827999999美元，相差约3×10^-14美元，来自SQLite插入顺序变化。新核验器仅对这一字段允许绝对误差≤10^-12，其它字段必须完全一致，不将尾差算成新增费用。

新增数据库需满足252唯一job、7453唯一job/step、每局步数与动作行数一致。所有局部前缀SHA一致，替代动作≤3，未新增模型响应。治理夹具在M0副本比较原有记账与“direct_use_count>0才记直接usage”门控，只证明信用更新差异，未重跑策略或改变历史评分。

阶段B未执行；本轮API调用0、费用0元。若需新模型后续行为，先另外申请，不能把旧响应重放当成提示修复后的模型输出。

## 仅核对公开恢复和已保存回执

除上面的完整Linux/JVM回放外，可在安装既有统计依赖的Python环境执行纯静态检查。先按上文恢复、准备快照并运行旧统计脚本到 recompute/output，然后运行 root_cause_audit.py。用下面命令序列化本分支已保存的真实JVM回执并核对其事实分支与历史轨迹哈希：

```bash
$PYTHON scripts/root_cause_counterfactuals.py --root .. \
 --summarize-receipts artifacts/root_cause_counterfactual_receipts.json
$PYTHON scripts/root_cause_public_verify.py --root ..
# 依赖固定上游FlowEvo源码；仅运行原函数的记账逻辑，不导入模型客户端。
$PYTHON scripts/root_cause_governance_check.py --root .. \
 --flowevo-source ../vendor/FlowEvo
```

此路径不重新执行JVM，回执明确标记这一点。root_cause_private_reference.json 是断连前下载的私有分析文件SHA，用于交叉核对，不是另一组模型实验。治理检查从冻结Git对象提取原样的restore_trace/publish_batch函数体，并使用固定上游真实SkillLibrary；没有用Mock替代记账实现。本机二次复算使用Python 3.13.12；正式JVM诊断仍使用服务器固定环境，具体版本见运行回执。

发布扫描使用 root_cause_scan_publication.py，检查已跟踪/新增文件、暂存差异、全部可达Git blob及zstd解压内容中的凭据模式，不打开密钥文件。模式扫描不能保证发现任意未知格式秘密；历史精确密钥扫描回执保留原样，本轮没有再次读取真实API Key。
