# 服务器退役备份：从GitHub继续工作

完整文件存放在[GitHub Release附件](https://github.com/ChenKaichen-SCUT/Flowevo_failure/releases/tag/server-backup-20261117)，恢复代码和中文说明位于 `backup/server-retirement-20261117` 分支。

**请保存另行交付的 `RECOVERY_KEY.txt`。公开GitHub只存密文，完整恢复必须使用这份密钥。** 不要把密钥提交到GitHub；Release的 `Source code.zip` 也不包含加密附件。

- 135,307个文件，覆盖六个项目目录的全部代码、Git历史、原始轨迹、账本、私有任务清单、凭据、技能库、报告和原Python环境。
- 同时保留固定上游源码/JAR、Java 11、依赖缓存与系统版本清单。
- 原始文件11,660,940,012字节，去重压缩并加密后3,256,171,836字节，共25个分片。
- 已在空目录恢复全部文件并逐文件校验；恢复环境56项测试通过，实际JVM加载历史TRAIN任务通过，无新增模型调用。
- 不包含操作系统镜像、root SSH私钥、shell历史及无关系统目录。

按[完整恢复说明](reports/SERVER_RESTORE_ZH.md)下载、解密、验证，再建立新的工作分支。推荐Ubuntu 22.04 x86_64 / Python 3.10。

[备份清单](artifacts/server_backup/backup_manifest.json) · [完整恢复校验](artifacts/server_backup/restore_verification.json) · [恢复环境验证](artifacts/server_backup/offline_smoke.json) · [加密工具测试](artifacts/server_backup/snapshot_tests.json)
