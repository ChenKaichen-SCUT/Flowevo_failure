# FlowEvo–ScienceWorld 服务器退役完整备份

原服务器的六个项目目录全部文件已归档，并保留固定上游源码/JAR、Python环境、Java 11、pip缓存及系统安装清单。包括原始实验轨迹、模型请求响应、私有任务清单、SQLite账本、技能库、审计报告和已有凭据。

**附件采用AES-256-GCM认证加密。完整恢复需要另行交付到用户电脑的 `RECOVERY_KEY.txt`；密钥不在GitHub。** 请保存密钥，不能只下载代码ZIP。

135,307个文件，原始11.66GB，去重压缩加密后3.26GB。下载全部25个 `flowevo-server-snapshot.partNNNN` 和 `backup_manifest.json`。分片不需要手动拼接，恢复工具会按清单处理。

[中文恢复步骤](https://github.com/ChenKaichen-SCUT/Flowevo_failure/blob/backup/server-retirement-20261117/reports/SERVER_RESTORE_ZH.md) · [备份入口](https://github.com/ChenKaichen-SCUT/Flowevo_failure/blob/backup/server-retirement-20261117/SERVER_BACKUP_README.md)

验收：空目录全量恢复及逐文件SHA256校验通过，56项项目测试通过，使用恢复JAR启动JVM并加载历史TRAIN任务通过；错误密钥、篡改、路径和覆盖保护等5项备份工具测试通过。未新增模型API请求或费用。GitHub附件的实际回读校验记录随备份分支交付。

这是项目完整备份，不是系统盘镜像。新服务器推荐Ubuntu 22.04 x86_64 / Python 3.10。root SSH私钥、shell历史和无关系统目录不在备份内。旧服务器未被本流程删除。

GitHub附件的25个加密分片和清单共26项均已实际下载回读，SHA256全部一致。详见[回读验收记录](https://github.com/ChenKaichen-SCUT/Flowevo_failure/blob/backup/server-retirement-20261117/artifacts/server_backup/github_readback.json)。
