# 复现说明

本交付区分三种复现：无密钥的日志统计复算、真实 JVM 的保存动作回放、重新付费的模型实验。公开 TEST 已暴露，复跑它不能当成新的未见测试；模型别名及服务器响应也不保证逐字相同。

## 安装与目录

以下 Linux/Ubuntu 命令按此目录布局运行。Python 3.10、OpenJDK 11、git、python3-venv 为系统依赖。本次新服务器实际安装 OpenJDK 11.0.33，已有 Python 3.10.12。

```bash
sudo apt-get update
sudo apt-get install -y openjdk-11-jre-headless python3-venv git
mkdir -p flowevo-reproduction
cd flowevo-reproduction
git clone --branch feat/scienceworld-failure-invariants \
  https://github.com/ChenKaichen-SCUT/Flowevo_failure.git output
export PIP_INDEX_URL=https://mirrors.huaweicloud.com/repository/pypi/simple
bash output/scripts/bootstrap.sh "$PWD"
cd output
```

`bootstrap.sh` 获取固定 FlowEvo/ScienceWorld SHA，创建独立 `.venv`，安装 `requirements.lock.txt`，安装本项目并运行 26 项测试。上游 JAR 自带于固定源代码，不复制不同版本。参考的历史失败研究仓库不是运行依赖，没有复制其数据。

本次在服务器另一个全新目录实际执行安装、26 项测试和 5 种真实 JVM 回放，证据为 `artifacts/clean_reproduction.json`。回放模式覆盖动态、引导、直接、直接后回退以及 F-I 空规则；观察哈希与自主成功 TRAIN 原记录完全一致，无新 API 调用。它不是模型重新求解结果。

## 公开日志离线复算

在刚安装、尚不存在 `../runs-private` 的目录执行：

```bash
../.venv/bin/python scripts/restore_public_run.py --root ..
../.venv/bin/python scripts/analyze_results.py --root .. --runs \
  discovery-v2 selected-train-v1 dev-baseline-v1 \
  batch-sensitivity-1-v1 batch-sensitivity-8-v1 \
  main-order-17-v1 main-order-29-v1 control-order-17-v1
../.venv/bin/python scripts/summarize_audit.py --root ..
../.venv/bin/python scripts/verify_reproduction.py --root .. --run-id discovery-v2
```

还原器只解压公开脱敏的自有记录，不接触模型接口、不读取密钥。它拒绝覆盖现有 `runs-private`。逐任务 CSV 和汇总数值应相同；还原后 JSON 字节排版可能改变，因此重算输入文件的字节哈希与私有原件可能不同。原始 SHA 映射仍见 `results/export_mapping.json`。离线复算验证记录另见 `artifacts/offline_reproduction.json`。

## 新的真实模型实验

使用另一份独立安装，不要在刚还原的原始 Run ID 上启动新调用。先保存交付 `artifacts` 目录的只读副本并在工作副本中使用空 `artifacts`；避免加载交付结果当作新实验输出。后续命令为本次实际使用过的入口和参数，单次全流程只有一个共享协调器。运行前核对当日官方价格，代码中预算费率必须与审核后的配置一致；本次价目快照和 100 美元上限保留在 artifacts/configs 中。

将自己的单行 DeepSeek 密钥放到仓库外 `../secrets/api.txt`，权限 600、目录 700。不要将密钥放入命令参数、仓库或公开日志。启动协调器并等健康检查成功：

```bash
mkdir -p ../runs-private ../secrets
chmod 700 ../secrets
chmod 600 ../secrets/api.txt
nohup ../.venv/bin/python -m flowevo_sw.request_scheduler \
  --api-key-file ../secrets/api.txt --private-dir ../runs-private \
  --budget 100 --concurrency 16 > ../runs-private/scheduler.log 2>&1 &
curl --fail http://127.0.0.1:8765/health
```

如果健康检查尚未成功，先等服务启动，不要在失败连接上建立吞吐结论。原始阶梯校准有一次启动竞态，另 Run ID 重做，费用均保留。重新校准时按 `api_ladder.json` 规则选择并发；本次 8/16/8 各 32 个无解题内容请求，16 吞吐为 8 的 1.70 倍，环境 8 路。

```bash
../.venv/bin/python scripts/freeze_tasks.py --root ..
../.venv/bin/python scripts/freeze_setup.py --root ..
../.venv/bin/python scripts/audit_environment.py --root ..
../.venv/bin/python scripts/calibrate_api_ladder.py --root .. --run-id calibration-ladder-v2
../.venv/bin/python scripts/run_discovery.py --root .. --run-id discovery-v2 --workers 8 --per-type 2
../.venv/bin/python scripts/learn_constraints.py --root .. --discovery-run discovery-v2 --run-id learning-v2
../.venv/bin/python scripts/select_tasks.py --root .. --mechanisms ../runs-private/learning-v2.mechanisms.json
../.venv/bin/python scripts/probe_hypotheses.py --root .. --mechanisms ../runs-private/learning-v2.mechanisms.json --run-id train-probes-v1 --all-hypotheses
../.venv/bin/python scripts/adjudicate_probes.py --root .. --probe-index ../runs-private/train-probes-v1.index.json --mechanisms ../runs-private/learning-v2.mechanisms.json
../.venv/bin/python scripts/run_selected_train.py --root .. --run-id selected-train-v1 --discovery-run discovery-v2 --workers 8
../.venv/bin/python scripts/generate_rules.py --root .. --probe-index ../runs-private/selected_probes.json --run-id rules-v1
../.venv/bin/python scripts/revise_rules.py --root .. --revision 1
../.venv/bin/python scripts/validate_dev.py --root .. --bank ../runs-private/selected-train-v1.F.final_bank.json --workers 8
../.venv/bin/python scripts/dev_local_validation.py --root .. --bank ../runs-private/selected-train-v1.F.final_bank.json --run-id dev-local-v2
../.venv/bin/python scripts/batch_sensitivity.py --root ..
```

若无可检验机制或准入规则，按有限停止规则保留结果，不强行启动 TEST。当前最终代码包含 TEST 前修复后的证据压缩与 F-S 边界；重新从头运行不重现初版缺陷，初版请求已公开保留以供审计。不能为了追求原报告数字而追加未声明修订。

在打开 TEST 前提交源码、冻结配置中的 source_commit，并核对 `dev_validation.json`、M0、任务清单和费率。协调器及所有组应使用相同冻结代码，不热更新运行时。正式命令会原子保存协议和 SHA；已有不同协议将拒绝覆盖。

```bash
../.venv/bin/python scripts/run_main.py --root .. \
  --bank ../runs-private/selected-train-v1.F.final_bank.json \
  --validation artifacts/dev_validation.json --workers 8 --test-per-type 6
../.venv/bin/python scripts/analyze_results.py --root .. --runs \
  discovery-v2 selected-train-v1 dev-baseline-v1 \
  batch-sensitivity-1-v1 batch-sensitivity-8-v1 \
  main-order-17-v1 main-order-29-v1 control-order-17-v1
../.venv/bin/python scripts/summarize_audit.py --root ..
../.venv/bin/python scripts/export_public_artifacts.py --root .. \
  --api-key-file ../secrets/api.txt --runs \
  discovery-v1 discovery-v2 selected-train-v1 dev-baseline-v1 \
  batch-sensitivity-1-v1 batch-sensitivity-8-v1 \
  main-order-17-v1 main-order-29-v1 control-order-17-v1
../.venv/bin/python scripts/scan_publication.py --repo . --api-key-file ../secrets/api.txt
```

断线后重用原命令/Run ID 会读取已锁定结果和已结算响应，并逐步核对重放前缀；UNKNOWN 保留预算且禁止自动重发。不同协议必须使用独立工作目录/Run。日志中的正常失败不可用选择性重跑覆盖。主统计仅使用完整五组配对块，缺失单列。

## 发布与版本

本次主实验运行源码为 `05ad11cae6c7ebf89a843fed9f3d75b584c06c8d`；配置内 source_commit 指向紧邻的代码冻结提交 `acfdd9f5c3564460b7098a88ba7521ee29ef6e97`，二者运行时代码相同，后者之后只加入冻结配置/证据。发布提交后来增加离线复算、脱敏、汇总和报告工具，并让 `freeze_setup.py` 的历史仓库依赖可选；没有修改已经执行的评分、模型、约束或主统计脚本。

`publish_results.sh` 先扫描工作树、暂存 diff、待推历史和压缩包解压内容，再正常 commit/push 并核对远端 SHA；需要已配置 GitHub 凭据。本次服务器成果通过 Git bundle 转到拥有写权限的本地 Git 后正常推送同一新分支，不使用 force push。远端最终版本以分支 HEAD 和交付消息为准，避免自引用提交哈希。
