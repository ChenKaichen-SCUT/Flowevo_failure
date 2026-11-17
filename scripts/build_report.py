"""Render Chinese report from frozen, read-only analysis products; no model calls."""
import argparse,json,csv,collections,datetime
from pathlib import Path

def table(headers,rows):
    return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(str(v) for v in row)+'|' for row in rows])
def pct(x):return f'{100*x:.2f}%'
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();out=Path(a.root).resolve()/'output';s=json.loads((out/'results/summary.json').read_text());audit=json.loads((out/'results/audit_summary.json').read_text());protocol=json.loads((out/'artifacts/protocol.json').read_text());delivery=json.loads((out/'artifacts/delivery_audit.json').read_text());rows=list(csv.DictReader((out/'results/episodes.csv').open()));arms=['F','F-I','F-T','F-S','F-H'];g=s['groups'];cmp=s['comparisons']['F-I_vs_F'];tests=[r for r in rows if r['population']=='test'];bycost=audit['costs_by_run_arm_stage']
    def armcost(arm,prefix='main-'):
        cc=collections.Counter()
        for key,v in bycost.items():
            run,a,stage=key.split('/')
            if run.startswith(prefix) and a==arm:cc.update(v)
        return cc
    primary_rows=[];skillrows=[];costrows=[];verdictrows=[]
    for arm in arms:
        d=g['test/'+arm];mech=d['mechanism_counts'];rr=[r for r in tests if r['arm']==arm];c=armcost(arm);ve=[v for v in audit['veto_events'] if v['arm']==arm and v['job_id'].startswith('main-')]
        primary_rows.append([arm,f"{d['successes']}/{d['locked_denominator']}",pct(d['completion_rate']),f"{d['type_equal_score_mean']:.2f}",f"{sum(float(r['highest_score']) for r in rr)/len(rr):.2f}",d['missing']])
        skillrows.append([arm,mech['retrieval_opportunity'],mech['template_retrieved'],mech['binding_accepted'],mech['direct_executions'],mech['direct_successes'],mech['guided'],mech['fallback'],mech['native_holdout']])
        costrows.append([arm,mech['actual_actions'],int(c['requests']),int(c['prompt_tokens']),int(c['completion_tokens']),f"{c['estimated_peak_usd']:.6f}"])
        verdictrows.append([arm,mech['allow'],mech['veto'],mech['abstain'],sum(v['changed_action'] for v in ve),len({(v['job_id'],v['checkpoint']) for v in ve}),sum(r['failure_type']=='PERSISTENT_CONSTRAINT_CONFLICT' for r in rr)])
    families=sorted(g['test/F']['by_task']);familyrows=[]
    for task in families:
        familyrows.append([task]+[f"{g['test/'+arm]['by_task'][task]['success']}/{g['test/'+arm]['by_task'][task]['n']}" for arm in arms])
    orderrows=[]
    for run in ['main-order-17-v1','main-order-29-v1']:
        rr=[r for r in tests if r['run_id']==run]
        orderrows.append([run]+[f"{sum(r['success']=='True' for r in rr if r['arm']==arm)}/12" for arm in arms]+[f"{100*cmp['order_deltas'][run]:+.2f} pp"])
    failrows=[]
    for arm in arms:
        rr=[r for r in tests if r['arm']==arm]
        failrows.append([arm,sum(r['termination_reason']=='NEGATIVE_SCORE' for r in rr),sum(r['termination_reason'] in ('HOST_STEP_LIMIT','ENVIRONMENT_STEP_LIMIT') for r in rr),sum(r['failure_type']=='PERSISTENT_CONSTRAINT_CONFLICT' for r in rr),sum(r['failure_type']=='ACTION_PARSE_ERROR' for r in rr),sum(r['failure_type']=='DELIVERY_TRUNCATED' for r in rr),sum(r['status']!='EPISODE_LOCKED' for r in rr)])
    comparisonrows=[]
    for name,d in s['comparisons'].items():
        lo,hi=d['hierarchical_bootstrap_95_ci'];comparisonrows.append([name,f"{100*d['type_equal_completion_delta']:+.2f} pp",f"[{100*lo:+.2f}, {100*hi:+.2f}] pp",d['F_I_only_success_order_pairs'],d['comparator_only_success_order_pairs']])
    controlrows=[]
    for arm in arms:
        d=g['control/'+arm];controlrows.append([arm,f"{d['successes']}/{d['locked_denominator']}",f"{d['type_equal_score_mean']:.2f}",d['mechanism_counts']['direct_executions'],d['mechanism_counts']['direct_successes']])
    comp_rows=[]
    for run in ['discovery-v2','selected-train-v1','dev-baseline-v1','main-order-17-v1','main-order-29-v1','control-order-17-v1']:
        c=audit['compilation'].get(run,{});gov=audit['governance'].get(run,{})
        comp_rows.append([run,c.get('successful_episodes_submitted',0),c.get('valid_templates',0),c.get('template_rejections',0),gov.get('templates_admitted',0),c.get('guidelines',0),gov.get('audits',0)])
    stage=collections.defaultdict(collections.Counter)
    for k,v in bycost.items():stage[k.split('/')[-1]].update(v)
    stage_rows=[[(k+'（含未独立标 stage 的诊断/校准）') if k=='action' else k,int(v['requests']),f"{v['estimated_peak_usd']:.6f}"] for k,v in sorted(stage.items())]
    timing=audit['timings'];main_runs=['main-order-17-v1','main-order-29-v1','control-order-17-v1'];first=min(timing[r]['first_request'] for r in main_runs);last=max(timing[r]['last_response'] for r in main_runs);span=last-first;summed=sum(timing[r]['summed_request_seconds'] for r in main_runs);res=audit['resource_sampling']
    fi_veto=[v for v in audit['veto_events'] if v['arm']=='F-I' and v['job_id'].startswith('main-')];ft_veto=[v for v in audit['veto_events'] if v['arm']=='F-T' and v['job_id'].startswith('main-')];ft_extra=sum('VETO' not in v['executable_FI_decisions'] for v in ft_veto)
    shadow=collections.Counter(v['rule_arm'] for v in audit['posthoc_baseline_opportunities'] if v['job_id'].startswith('main-'))
    primary_delta=100*cmp['type_equal_completion_delta'];lo,hi=[100*x for x in cmp['hierarchical_bootstrap_95_ci']]
    report=f'''# FlowEvo–ScienceWorld 真实实验中文报告

本轮完成了服务器部署、固定版本适配、真实 DeepSeek 探索/学习/开发/TEST、离线统计和复现验证。主比较 F-I 为 {g['test/F-I']['successes']}/24，完整 FlowEvo 适配基线 F 为 {g['test/F']['successes']}/24；完成率差 **{primary_delta:+.2f} 个百分点**，分层 bootstrap 95% 区间 **[{lo:+.2f}, {hi:+.2f}]**。只有 2 个任务家族、12 个独立 TEST variation，每题两种顺序，不能将 24 次测量当作 24 个独立任务，也不能据此确立普遍优势。

F-I 与文字规则组 F-T 持平，低于成功后缀组 F-S 的 {g['test/F-S']['successes']}/24；人工简单规则组 F-H 为 {g['test/F-H']['successes']}/24。F-I 有 3 局因持续否决而提前停止。这里不能给出稳定增益或优于简单对照的结论。

这是有真实运行支撑的小样本 pilot。可信状态机制只确认了门和容器的简单开闭前提；复杂的温度、电路、阶段保护或旧状态失效没有达到本轮准入证据门槛。完整基线未被关闭成功技能或减少预算。任何数值优势都需要与文本经验、成功后缀、人工简单规则和额外计算一起解释。

## 1. 协议与完成范围

固定 FlowEvo `36e81efd4d1fdbabca7366200b15808ebef157fa`，ScienceWorld `e8216d6044e8e39be9fcb185e3b2dfb602584b52`（1.3.0）、Python 3.10.12、OpenJDK 11.0.33。JAR 指纹、依赖锁、官方 split 哈希见 artifacts。原始 30 类、TRAIN 3592 / DEV 1796 / TEST 1819，未跨 split 补齐。全部模型阶段统一 `deepseek-flash`、非思考、temperature=0，动作输出上限 4096、学习 8192；别名不能证明底层权重不可变。

无 simplification，episode_limit=100，所有实际动作经统一网关。主成功要求原生完成且最终官方 score=100；保留普通环境反馈，隐藏数值 score、Gold、目标内部进度和世界对象树不进入模型。合法动作接口为完整官方 valid-action-assisted，不按正确答案过滤、不自动选首个合法动作。

|阶段|完成情况|用途|
|---|---|---|
|完整覆盖 TRAIN|30 类 × 2 = 60 局，17 成功|固定 SHA 抽样、失败机会审计|
|额外所选 TRAIN|2 类 × 10 = 20 局，10 成功|每类累计 12 variation，共同 M0|
|TRAIN 替代探针|12 假设 × 2 = 24 个替代分支|最多 8 动作，同前缀核对|
|DEV 完整基线|2 类 × 4 = 8 局，4 成功|自然机会、候选筛查|
|DEV 受控分支|20 条|局部功能，独立于整局成绩|
|主 TEST|2 类 × 6 variation × 2 顺序 × 5 组 = 120 局|全部锁定、0 缺失|
|范围外 TEST 对照|2 类 × 2 variation × 5 组 = 20 局|独立 M0、单顺序，单列|
|批次敏感性|相同 4 TRAIN × 2 设置 = 8 局|重复 TRAIN，不算独立评测|
|废弃工程校准|discovery-v1 16 局|原件/成本保留，效果不并入|

主任务为斜面摩擦具名表面和寻找动物，由 TRAIN 同前缀修复证据选择；范围外遗传已知植物和最短寿命任务也在 TEST 前选定。没有挑选 F-I 获胜的 TEST。各组/各顺序独立成功库，批量大小 8，批内冻结、批末按固定顺序成功编译及原生治理；失败规则在 DEV 后冻结。不是逐题立即在线。

主运行源码 `{protocol['source_commit']}`；协议 SHA-256 `{protocol['protocol_sha256']}`。最终检查确认冻结运行时代码未变化、批内库一致、三种总体共同 M0；{delivery['provider_requests_audited']} 个实际请求只到官方 DeepSeek，结构化请求未含禁止的隐藏评分字段。查看 `delivery_audit.json`。

## 2. 预声明主要比较及不确定性

{table(['组','完成数','完成率','最终 score 类型等权均值','最高 score 均值（仅描述）','缺失'],primary_rows)}

最高分与最终分分开，主指标使用最终完成；负分按官方原始值保留，未截为零。

{table(['比较','完成率差','分层 bootstrap 95% 区间','仅 F-I 成功的顺序配对','仅比较组成功的顺序配对'],comparisonrows)}

主比较先看 F-I 对 F，其余为预声明描述性次要比较，不用多个未经校正的 p 值选显著结果。先在每个 task/variation 内平均两个顺序，再按家族、variation 两层有放回抽样 10000 次。家族仅两个，在线库让同一顺序中的任务进一步相关，区间仅用于展示有限数据的不确定性，不是充分建模所有在线依赖。没有将动作、调用或工程测试当独立统计样本。

{table(['任务家族']+arms,familyrows)}

{table(['任务顺序']+arms+['F-I − F'],orderrows)}

{table(['组','官方负分终止','步数预算耗尽','持续约束冲突','最终解析失败','交付截断','基础设施缺失'],failrows)}

表中后三类不是普通任务未完成；其中持续冲突为规则系统自己的终止代价。中途格式错误若已在统一一次接口修复内恢复，不算新的失败局，原请求解析状态仍保留。

## 3. 是否真实保留成功技能链路

直接继承上游 `AlfWorldExecutor.run` 和 `AlfWorldCompiler.compile`，复用三层库、检索、参数化实例化、准入和治理。环境专用动作循环、公开状态、严格解析与 DeepSeek 网络层作适配。原生 L2/L3 20% holdout、1337 RNG、20 局审计继续运行，L1 不被全局关闭。详见适配报告的逐文件映射。

TRAIN 自然进入直接路径 2 次：`find-non-living-thing` 实际执行 5 个技能动作并直接成功；`lifespan-shortest-lived` 第一个模板动作不适用，实际直接动作 0，回退引导成功。直接路径进入计数不等于实际动作执行数，明细见 `audit_summary.json` 的 `direct_routes`。主 TEST 各组统计如下；“检索到模板”与“绑定接受/执行”分开，不能把不可适用模板的存在算复用收益。

{table(['组','有技能检索','模板检索','绑定接受','直接执行','直接成功','引导局','回退局','原生留出'],skillrows)}

{table(['Run','成功编译数','来源验证合格模板','模板验证拒绝','原生模板准入','产生引导','原生审计次数'],comp_rows)}

模板必须实例化为真实成功轨迹动作的有序子序列；参数把 hallway/workshop 等不同地点混合时明确拒绝，不手填正确解法。引导仍可入库。各类型实际调用及治理状态变化保留在 audit_summary 和批次库记录。相同成功轨迹的五种真实 JVM 回放证明路径接通，不能代替自然迁移效果。本轮主 TEST 直接执行为零：公开状态绑定均未接受；范围外对照每组直接调用一次但均未直接成功。因此不能宣称主任务已验证“约束增强直接技能复用”的自然收益。

## 4. 可信状态错误、学习来源与迁移

30 组诊断得到 12 个两 variation 引文假设。24 个实际替代分支中，仅关闭门/容器的两个机制各取得两次“准备状态后同一动作可用”。其余植物死亡、生长阶段、温度漂移、排水等可能存在真实状态变化，但缺少本轮可复现的局部修复；编号歧义/对象指代偏接口，温度解释/电路设计还涉及科学知识与探索。不能把所有低分归为状态遗忘。

F-I 来自失败/恢复对比，F-S 来自同一证据子集的成功恢复后缀，F-T 获得与 F-I 相同的完整规则语义，F-H 为公开人工规则。共享状态解析只提取当前 look 明示的对象开闭；所有组相同。模型生成两条 F-I 规则和一条 F-S 规则，F-S 容器保留空候选。每机制一次初次生成、一次修订，未耗尽最多两次修订额度。

初版存在需保留的负面工程证据：重复合法动作列表造成超大输入及错误极性规则；F-S 意外见到失败前观察。TEST 前修复为 compact-public-v2，清除 F-S 失败输入和旧解释，全部旧请求、失败与成本保留。没有据 TEST 结果修订。具体规则和别名限制见 `CONSTRAINT_LEARNING_REPORT.md`。

DEV 受控 20 分支验证覆盖新 variation、bee hive/fridge 和 outside/kitchen 门，确认实际改变动作及状态变化后的放行，unknown、等待、撤销边界通过。来源修复和新对象局部功能均不能自动推出整局成功。F-S 门的两个共同证据案例与 F 均用 8 动作，无效率优势；两组学到不同保护条件，所以本试验没有干净识别失败对比本身的独立因果贡献。

## 5. 自然介入、文字审查与负迁移

{table(['组','ALLOW 次数','VETO 次数','ABSTAIN 次数','否决后实际换动作','否决检查点数','持续冲突停止局'],verdictrows)}

计数单位是规则判定，F-I/F-H 每候选可有两条判定，F-T 每候选为一次文字审查，不能把分母混用。F 本身没有规则判定。每检查点最多一次重新规划，真实动作仍共享 100 次预算。

主 TEST 的 F-I 共 {len(fi_veto)} 次否决，其中 {sum(v['changed_action'] for v in fi_veto)} 次后续真实动作改变；所在局成功数为 {len({v['job_id'] for v in fi_veto if v['episode_success']})}，这只是相关事实，不能说每次否决导致获胜。事后将冻结规则在 F 的已执行轨迹上被动筛查，F-I/F-S/F-H 匹配分别为 {shadow['F-I']}/{shadow['F-S']}/{shadow['F-H']} 次；这是机会描述，不是补做 TEST 干预。

F-T 自然否决 {len(ft_veto)} 次，其中 {ft_extra} 次在同一公开状态和动作上不会被 F-I 声明式条件否决，包含把房间 look-in 解释为门规则的情况。它显示文字审查可扩展或误读语义；未执行动作的反事实未知，不能直接将其全部定为错误否决。已观察到的代价包括重新规划成另一无益操作（如已开的门），以及 F-I 的 3 局、F-H 的 2 局持续冲突停止。这是可观测的规则运行负面后果，不能隐去。局部边界测试未发现必要等待/撤销被拦，不能宣称自然误触发率为零，也没有独立标注足以估计该率。

没有给 F-I 更长历史、更强模型或隐藏反馈；额外规则语义与复核/重规划计算按组记录。F-T 可审查直接技能候选；自然直接路径触达不足时不将其算作验证过的覆盖收益。temperature=0 的远程模型仍产生运行差异，在线成功库进一步放大路径差异；只有一次自然否决的 F-S 也取得不同成绩，不能把组间所有分差都解释为规则因果效果。不能仅凭这些小样本差异把优势归因于可执行化、失败对比或规则本身。

## 6. 选择范围外对照

{table(['组','成功/4','最终 score 均值','直接执行','直接成功'],controlrows)}

各组一次自然直接路径在最短寿命任务上实际执行 2 个技能动作，再因公开动作不适用而回退，最终整局成功。F-T 对这 2 个直接动作也真实执行了文字审查；它能触达 L1，并非人为禁止其影响直接技能。该总体只有 4 个独立 variation、1 个顺序，从共同 M0 另起，各组不继承主 TEST 库。它用于观察容易成功/机制不适用的任务，不合并进主比较分母，也不能选其中最好结果作为迁移结论。

## 7. 成本、并行与复现

全流程真实请求 **{s['costs']['requests']} 次**，按冻结峰值价和供应商 usage 估算 **${s['costs']['estimated_peak_usd']:.6f}**，低于授权 $100；未结算预留 **${s['costs']['unresolved_reservation_usd']:.6f}**。输入 {s['costs']['prompt_tokens']:,}、输出 {s['costs']['completion_tokens']:,} token。包括废弃 v1、启动校准、失败生成、规则修订、探针、DEV、所有成功编译及 TEST；供应商实际账单未获取，不能将估算冒充扣款总额。

主 TEST（含相应成功编译/绑定）的资源如下：

{table(['组','实际环境动作','API 请求','输入 token','输出 token','峰值价估算 USD'],costrows)}

全阶段费用审计：

{table(['阶段','请求数','估算 USD'],stage_rows)}

action 阶段包含 30 次失败诊断及无解题内容校准，它们的请求 ID/调用内容可单独审计；并未把全部该阶段费用称为求解费用。原生治理为本地计算，包含在运行墙钟中，不产生额外模型请求。规则运行本地判定的 CPU 成本没有单独高精度计时；模型复核与约束重规划均在账本，不宣称“约束免费”。F-I 动作和推理费用较少的一部分来自持续冲突提前停止，不能直接等同于更高效率。本轮数据不足以证明额外学习和运行成本能稳定换取收益。

正式 main+control 从第一条请求到最后响应共 {span:.2f} 秒（{span/60:.2f} 分钟，未含最初 JVM 启动），各请求耗时相加 {summed:.2f} 秒。差额是并发重叠的描述，不能当作实测串行节省；没有把全部正式实验再串行重跑，因此严格的端到端加速倍数未知。独立短请求 8/16/8 校准实测吞吐提升 1.70 倍，不能外推成整套任务 1.70 倍加速。

机器 4 CPU、约 30 GiB RAM，使用 8 环境/16 API；资源采样最大观测实验 RSS {res['max_observed_experiment_rss_gib']:.2f} GiB、最少可用内存 {res['min_available_memory_gib']:.2f} GiB、全机平均 CPU {res['mean_cpu_percent']:.2f}%。5 秒采样可能漏瞬时峰值，且包含并行的干净复现，最多 {res['max_java_processes']} JVM 不等同于正式环境池大小。小环境测试记录的是结束 RSS，不是峰值。

在独立目录完成固定依赖安装、26 项边界测试及真实 JVM 五种路径回放。公开压缩日志可无密钥恢复并重算统计；最终离线对照验证见 `offline_reproduction.json`。全部私有原件留服务器仓库外，公开文件附 SHA 映射；实际 API Key、常见凭据模式、暂存 diff、所有待推历史和压缩解包内容经过扫描。未用 TEST 清单、私钥和密钥不公开。已完成的 TEST 轨迹一经公开即视为暴露。

## 8. 证据支持的结论与后续决定

本次已证明完整适配具备真实成功编译、检索、引导、直接执行、动态回退和治理，且可学习并执行少量公开状态前提。但只确认两个简单开闭机制，DEV 自然触发很少；没有建立足够丰富的状态失效机制，也没有凭本轮小样本确立 F-I 相对所有对照的稳定、成本合理的普遍优势。数值结果全部按冻结协议呈现，允许无收益、持平和负迁移。

最受支持的限制是：valid-action-assisted 与原生成功技能已消除不少简单前提错误，剩余大量失败涉及实验知识、对象指代、探索或终止；两条局部规则无法解决这些问题。不能为了增加收益而关闭完整基线或缩短它的预算。

下一步应先停止在相同两条简单规则和已暴露测试上追加调参。若开展独立新研究，应预先选定能够公开观察阶段变化/旧状态失效的新机制与未暴露划分，验证两状态差异后再投入测试；同时改进通用成功编译/绑定只能作为各组共同工程改进。不能从本结果宣称 ScienceWorld 完全没有状态约束价值，也不能据单个局部正例声称路线成立。

复现命令见 `../REPRODUCE.md`；原始逐任务 CSV、所有正负规则版本和脱敏请求响应随分支提供。
'''
    (out/'reports/FINAL_REPORT_ZH.md').write_text(report,encoding='utf-8')
    readme=f'''# FlowEvo–ScienceWorld 失败对比状态约束实验

已完成真实服务器运行与 DeepSeek 实验。主 TEST 120 局、范围外对照 20 局，全部完成，无缺失。主要 F-I 为 {g['test/F-I']['successes']}/24，完整 F 为 {g['test/F']['successes']}/24，差 {primary_delta:+.2f} 个百分点，分层 bootstrap 95% 区间 [{lo:+.2f}, {hi:+.2f}]。F-I 与 F-T 持平、低于 F-S 的 {g['test/F-S']['successes']}/24，且有 3 局持续否决停止。这是两个任务家族的小样本 pilot，不能确立普遍优势。全流程峰值价估算 ${s['costs']['estimated_peak_usd']:.6f}，包含废弃运行和开发成本。

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
'''
    (out/'README.md').write_text(readme,encoding='utf-8');print('Rendered report and README from locked analysis')
if __name__=='__main__':main()
