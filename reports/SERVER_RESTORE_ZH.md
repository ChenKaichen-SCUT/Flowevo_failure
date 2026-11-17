# 删除服务器后的完整恢复说明

本备份用于在新机器继续FlowEvo–ScienceWorld工作，不依赖旧服务器。公开仓库保留代码、脱敏结果和报告；原始项目文件作为AES-256-GCM认证加密快照存放在GitHub Release附件中。**完整恢复需要GitHub附件和另行交付的 `RECOVERY_KEY.txt`，缺少密钥无法解密。** 密钥不能上传到公开仓库。

## 备份覆盖范围

- 六个项目目录的全部文件：`flowevo-scienceworld`、`flowevo-root-cause`、`flowevo-engineering`、`flowevo-success-trace`、`flowevo-repro-check`、`flowevo-offline-check`。包括隐藏文件、Git历史、未提交文件、原始请求响应、SQLite账本、技能库、私有任务清单、已有凭据、临时分析记录和已有Python虚拟环境。
- 原安装的固定版本上游源码及Git对象、ScienceWorld JAR、Java 11目录和Java配置、pip缓存。
- Ubuntu版本、系统安装包清单、Python/Java版本、pip冻结清单。
- 文件级清单和哈希在加密包内；公开的[备份清单](../artifacts/server_backup/backup_manifest.json)记录范围、数量、分片大小及SHA256。没有为节约体积删除项目文件，通过内容去重压缩存储。

这不是整块系统盘镜像。不含root SSH私钥、shell历史、无关系统目录及操作系统本身。新机器需要操作系统及Python基础环境。快照中的旧pid/日志/Git配置仅作历史存档，不会自动启动服务或模型实验。API凭据只存在于加密快照内；离线恢复和验证不会使用它们。

## 1. 准备新服务器和文件

推荐与原环境一致的 **Ubuntu 22.04、x86_64、Python 3.10**。解压后的项目文件约11.66GB，下载的加密附件约3.26GB；建议在新服务器留至少30GB空闲空间。程序拒绝覆盖已有恢复目录。

```bash
sudo apt-get update
sudo apt-get install -y git python3.10 python3-cryptography iproute2 util-linux
git clone --branch backup/server-retirement-20261117 \
  https://github.com/ChenKaichen-SCUT/Flowevo_failure.git flowevo-backup
cd flowevo-backup
python3 scripts/download_server_backup.py --dest "$PWD/encrypted-backup"
```

也可以直接打开[GitHub Release](https://github.com/ChenKaichen-SCUT/Flowevo_failure/releases/tag/server-backup-20261117)，下载全部 `flowevo-server-snapshot.partNNNN` 和 `backup_manifest.json`，放在同一目录。`Source code.zip` 不包含这些附件，不能替代加密备份。

下载脚本使用[GitHub附件下载接口](https://docs.github.com/en/rest/releases/assets#get-a-release-asset)。若共享出口触发匿名API限流，可手动下载附件，或在当前进程环境中提供已有的 `GITHUB_TOKEN`；它只用于GitHub下载，跨域重定向会移除认证头，与模型API密钥无关。不要把令牌写入脚本或仓库。

将已另行保存的 `RECOVERY_KEY.txt` 复制到新服务器的安全位置，权限设为600。下例用 `/root/RECOVERY_KEY.txt`，不要把密钥值写进命令行或聊天。建议你同时在密码管理器或独立存储介质保存一份密钥。

## 2. 解密并恢复到独立目录

```bash
sudo python3 scripts/server_snapshot.py restore \
  --input "$PWD/encrypted-backup" \
  --key /root/RECOVERY_KEY.txt \
  --dest /srv/flowevo-restored
```

程序先核验各分片及整包哈希，再完成GCM认证，认证成功后才解压。它逐文件校验恢复结果，写入 `/srv/flowevo-restored/RESTORE_VERIFICATION.json`。项目内部绝对符号链接映射到恢复目录；指向系统Python等未捕获OS路径的链接仍由新系统提供。相同内容会恢复为独立文件副本，后续修改一个文件不会影响其它副本。

恢复后的主要位置：

| 内容 | 恢复路径 |
| --- | --- |
| 原始实验、私有数据、账本及凭据 | `/srv/flowevo-restored/root/flowevo-scienceworld/` |
| 根因诊断及冻结原始快照 | `/srv/flowevo-restored/root/flowevo-root-cause/` |
| 治理、动作接口、条件绑定工程修复 | `/srv/flowevo-restored/root/flowevo-engineering/` |
| 最新成功轨迹与信息保真审计 | `/srv/flowevo-restored/root/flowevo-success-trace/` |
| 固定版本上游源码 | `/srv/flowevo-restored/root/flowevo-scienceworld/vendor/` |
| 原Python依赖环境 | `/srv/flowevo-restored/root/flowevo-scienceworld/.venv/` |
| 原Java 11 | `/srv/flowevo-restored/usr/lib/jvm/java-11-openjdk-amd64/` |

## 3. 验证可以继续工作

```bash
sudo bash scripts/verify_restored_server.sh /srv/flowevo-restored
```

验证在仅有loopback的网络命名空间内执行：运行56项项目测试，检查恢复的原始账本，并使用恢复的JAR启动JVM、重置历史TRAIN的melt:4任务。不会选择动作、重新求解、请求模型或产生API费用。输出 `RESTORED_TESTS.txt` 和 `RESTORED_SMOKE.json`。导入路径必须位于恢复目录，避免误用旧机器遗留项目。

快照虚拟环境依赖原Python 3.10/Linux ABI。如果新系统不是相同版本，应按仓库 `requirements.lock.txt` 和固定上游提交重建虚拟环境，不能把旧二进制环境视为跨系统通用。原环境和上游内容已保留，不再需要从旧服务器取文件。

## 4. 建立新的工作目录

建议从GitHub新建工作分支，保留快照目录作为原始备份。服务器旧Git快照中有一个与GitHub最终审计提交内容相同、但提交ID不同的换行修正提交；不要直接强推旧快照分支覆盖GitHub。

```bash
RESTORED=/srv/flowevo-restored
PROJECT="$RESTORED/root/flowevo-scienceworld"
mkdir -p "$RESTORED/resume"
git clone --branch backup/server-retirement-20261117 \
  https://github.com/ChenKaichen-SCUT/Flowevo_failure.git "$RESTORED/resume/output"
ln -s "$RESTORED/root/flowevo-success-trace/runs-private" "$RESTORED/resume/runs-private"
cd "$RESTORED/resume/output"
git switch -c work/next-stage
export PYTHON="$PROJECT/.venv/bin/python"
export JAVA_HOME="$RESTORED/usr/lib/jvm/java-11-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$PATH"
export PYTHONPATH="$PWD/src:$PROJECT/vendor/FlowEvo/src:$PROJECT/vendor/ScienceWorld"
```

然后按[成功轨迹审计复算说明](SUCCESS_AUDIT_REPRODUCE.md)运行离线脚本，`--root` 指向 `/srv/flowevo-restored/resume`，原始核验的 `--original` 指向 `$PROJECT/runs-private`。`runs-private`恢复目录已存在，不要再次运行会拒绝覆盖的 `restore_public_run.py`。仅复算公开审计也可以完全不解密，直接用仓库原有脱敏归档。

需要完整原始实验时使用 `$PROJECT/runs-private`，其账本有8941次历史请求；不要把已完成run ID当作新实验重复提交。继续研究时保留原有信息边界：旧TEST已公开，不作为新测试；不使用正确答案、Gold或隐藏评分选择动作。后续模型实验需另行明确预算和运行配置，本恢复流程不会自动启动。

## 验收与密钥保管

具体文件数、加密摘要、恢复核验及GitHub附件验证见 `artifacts/server_backup/`。恢复脚本包含错误密钥、密文篡改、覆盖拒绝、路径穿越、跨分片认证标签和独立文件副本测试。

删除旧服务器前，必须保留 `RECOVERY_KEY.txt`。GitHub中有完整密文，但没有恢复密钥；这两者分开保存是为了保护公开仓库中的凭据、原始私有数据和未公开任务清单。
