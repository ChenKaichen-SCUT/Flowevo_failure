# 成功轨迹审计复算

父提交为 `5ae0dcdf80bf81c4f5acd34d24f75501ddda942b`。本阶段不改运行时代码，不运行任务求解，不调用模型，不重新计算任务成功率。

## 输入与标签

复用仓库已有的三个脱敏压缩归档。`restore_public_run.py` 可在独立根目录恢复 `runs-private`，名称沿用旧工具，但本次恢复的内容全来自已发布归档。服务器另对原始私有记录进行语义等值与字节哈希核验。恢复文件的字节哈希、原服务器文件哈希和规范化JSON语义哈希分别记录，避免把JSON格式差异当成数据变化。

`success_audit_prepare.py` 只投影原始公开轨迹，不读取编译结果。审阅者按配置中的标签定义逐条读轨迹。两份助手审阅及裁定保存在 `artifacts/success_audit`。审阅者不是两名人类专家；主审有项目背景，第二审阅分支在源审阅阶段只读源包。39条源审阅先冻结，再连接编译记录。复算使用这些已公开的人工式助手标注，不会再次调用模型重标。

完整JSON源包约76MB，属于已有归档的重复投影，不再重复提交；准备脚本可原样重建。可直接阅读的39份 `.txt` 源包、语义摘要和步骤索引均随分支交付。冻结核验只允许LF/CRLF换行差异，不接受内容改动。

## 执行

在Linux独立目录下将仓库放在 `output`，使用原固定依赖环境和固定FlowEvo上游源码。第一次恢复：

```bash
cd /root/flowevo-success-trace/output
export PYTHON=/root/flowevo-scienceworld/.venv/bin/python
export PYTHONPATH="$PWD/src:/root/flowevo-scienceworld/vendor/FlowEvo/src"
unshare -n -- bash
ip link set lo up
export FLOWEVO_OFFLINE_ONLY=1
unset DEEPSEEK_API_KEY OPENAI_API_KEY
# 只在独立目录尚无runs-private时执行；工具拒绝覆盖。
$PYTHON scripts/restore_public_run.py --root ..
$PYTHON scripts/success_audit_prepare.py --input ../runs-private --output .
$PYTHON scripts/success_audit_compile.py --input ../runs-private --output .
$PYTHON scripts/success_audit_transfer.py --input ../runs-private --output .
$PYTHON scripts/success_audit_reports.py --output .
$PYTHON -m pytest -q > ../tests-success.log
$PYTHON scripts/success_audit_verify.py --root .. \
  --original /root/flowevo-scienceworld/runs-private
```

最终原始服务器核验需要提供原目录；其它机器可以完成公开数据重算、表格/报告生成、静态检查及测试，但不能声称重新核对了无法访问的原服务器字节。`start.json`、原始核验回执和审阅冻结记录是本次实跑的记录，不应改写日期伪装为另一轮新审阅。`success_audit_adjudicate.py` 是首次裁定写入脚本，会拒绝覆盖既有冻结文件，正常复算不运行它。

## 统计边界

- 主统计为31个独立TRAIN/DEV task/variation；补充8条版本/重复轨迹单列。102条成功记录的总库存还包括63条跨组/重复TEST成功记录，TEST仅连接历史元数据，不参与本次过程标签、技能审阅或静态变体。
- `success_trace_audit.csv` 每个历史成功记录一行；`skill_information_loss.csv` 分开源证据、编译输入、raw输出、L1与L2及适用条件，未知不补成失败。
- 39份保存的编译响应通过缓存路径重新做来源验证，不生成新技能、不准入。2份缺少单独的编译文件，响应恢复不等于历史准入或拒绝状态已知。
- 12个静态检查只用TRAIN/DEV公开状态及明确标注的虚拟变化。正负温度替换检验固定绑定动作是否响应新读数，不是新环境测量，也不代表新模型会如何绑定。
- 保持初始绑定、每步有效动作验证、直接路径、引导和回退代码原样。没有评分驱动的参数选择、专家路径、新TEST成绩或新增API成本。

## 冻结文件的Git字节保留

`.gitattributes` 将冻结审阅JSON标为 `-text`，保留原始换行字节，包括混合LF/CRLF。来源标注与冻结哈希未修改。首次发布后的全新检出核验发现Git默认规范化会使一份原始混合换行文件无法复核；补充提交恢复原冻结字节并加入此规则。普通生成报告仍使用LF。
