"""Render this Phase-A report from audit tables and saved public evidence."""
import argparse,json,csv,collections
from pathlib import Path
from root_cause_audit import read,js,cohort
def table(h,rows):return '\n'.join(['|'+'|'.join(h)+'|','|'+'|'.join(['---']*len(h))+'|']+['|'+'|'.join(str(v).replace('|','/').replace('\n',' ') for v in r)+'|' for r in rows])
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve();out=root/'output';res=out/'results';rep=out/'reports';inp=root/'input-snapshot'
 def csvread(n):return list(csv.DictReader((res/n).open(encoding='utf-8')))
 tax=csvread('failure_taxonomy.csv');life=csvread('skill_lifecycle_audit.csv');steps=csvread('trajectory_decision_audit.csv');cf=csvread('minimal_counterfactuals.csv');summary=read(out/'artifacts/root_cause_summary.json');primary=[r for r in tax if r['cohort']=='PRIMARY_BASELINE'];failed=[r for r in primary if r['success']=='False'];ps=[r for r in steps if r['cohort']=='PRIMARY_BASELINE'];repeat=[r for r in ps if 'REPEATED_ACTION_SAME_VISIBLE_CONTEXT' in r['observed_labels']];recent=sum(r['repeat_feedback_in_recent_16']=='True' for r in repeat)
 comp=[r for r in life if r['event']=='COMPILATION' and r['cohort']=='PRIMARY_BASELINE'];usage=[r for r in life if r['event']=='RETRIEVAL_AND_BINDING' and r['cohort']=='PRIMARY_BASELINE'];rejected=[r for r in comp if r['source_validation_rejection']];collapsed=[r for r in rejected if r['collapsed_parameter_values'] and json.loads(r['collapsed_parameter_values'])];negative=[r for r in failed if r['termination']=='NEGATIVE_SCORE'];focus_end=sum(r['final_feedback'].startswith('You focus on') for r in negative)
 cohortrows=[[k,v['episodes'],v['successes'],v['episodes']-v['successes'],v['steps']] for k,v in summary['cohorts'].items()]
 categoryrows=[[k.removesuffix('_episodes'),v,summary['cohorts']['PRIMARY_BASELINE'].get(k.replace('_episodes','_failed_episodes'),0)] for k,v in summary['cohorts']['PRIMARY_BASELINE'].items() if k.endswith('_episodes') and not k.endswith('_failed_episodes')]
 scope=f'''本轮阶段 A 分析历史 **252 局、7453 个实际动作**。主要基线为 116 局、104 个独立 task/variation/split、3520 动作，42 成功、74 失败，覆盖全部 60 初始 TRAIN、20 额外 TRAIN、8 DEV、24 主 TEST F 和4范围外 TEST F。其余112局其它组、8局重复TRAIN敏感性、16局已废弃工程校准单列，绝不合并当成基线。已公开 TEST 仅作历史分析，未进行新的 TEST 模型求解。

历史提交 `a0f6e0816c23a4abcb646a5fb018e786c2a6be95`。原服务器日志存在，复制所需文件到独立 `input-snapshot/` 后移除写权限，未复制 secrets。复用原统计及回放脚本在独立 recompute 目录运行，summary.json、episodes.csv、costs.csv 与发布版本逐字节一致。服务器分析与 JVM 回放在只有 loopback 的网络命名空间中运行，无法连接外部模型服务。另在本机从公开脱敏记录重建全部分析表，核心汇总及技能链路CSV与私有分析一致；历史费用求和只存在约3×10^-14美元的SQLite浮点尾差，详见零API复算说明。未读取 api.txt、未启动调度器。**新增 DeepSeek 调用 0 次，新增 API 费用 0 元。** 输入与运行回执见 artifacts/root_cause_input_manifest.json、root_cause_run_receipt.json、root_cause_public_reproduction.json。
'''
 taxonomy=f'''# 失败分类：直接终止、可见错误和可能根因

{scope}

{table(['总体','轨迹','成功','失败','动作'],cohortrows)}

`failure_taxonomy.csv` 每局一行，保留成功局以防仅观察失败导致偏差。`trajectory_decision_audit.csv` 每个实际动作一行，含目标、动作前 look/inventory/上次反馈、模型保存的 reason、动作后反馈和原记录 ID。证据引用 `episodes/<job_id>.json#/steps/<零基下标>`；行号 step 为一基。完整来源仍可用历史公开压缩记录恢复。

主要基线直接终止分布：{js(dict(collections.Counter(r['termination'] for r in primary)))}。59 次负分终止中，{focus_end} 次末条反馈为 You focus on；它是终止行为的关联描述，不能据此宣布所有 focus 都错误。成功局同样需要合法 focus。

{table(['可见标签（多选）','出现局数/116','其中失败局数/74'],categoryrows)}

标签来自明确反馈或保守字符串规则，非模型批量主观标注。CLOSED_ACCESS、UNRECOGNIZED_COMMAND、ELECTRICAL_TERMINAL 等指环境实际报告的局部问题；歧义菜单本身不是错误，正确数字选择是允许动作。FOCUS_AS_INSPECTION_LANGUAGE 是词汇候选，不等于已经证实的误用。重复仅表示动作、look、inventory和返回观察相同，可能仍有不可见时间变化；排除了 wait/activate/deactivate，仍不能将其全部归为无效。

上游根因允许 UNKNOWN / MULTIPLE_PLAUSIBLE_CAUSES。不能将 NEGATIVE_SCORE、100步耗尽或一个正则命中直接当作“缺少科学知识”。`causal_conclusion` 保守保留 INSUFFICIENT_EVIDENCE，局部反事实支持另见 minimal_counterfactuals.csv，不把局部存活当整局获胜。

六个检查型 focus 案例 CF01–CF06 用同对象 look at 替代，均避免当步负分终止，但没有任何一局因此在窗口内完成。这为动作语义/目标落地问题提供局部因果证据，不能估计一个改进提示词能恢复多少全任务成绩。所有未人工核查的类别均只作筛查，不声称可靠自然误判率。
'''
 (rep/'FAILURE_TAXONOMY_ZH.md').write_text(taxonomy)
 selected=[]
 def pick(predicate,n=1):
  for r in life:
   if predicate(r) and r not in selected:selected.append(r);n-=1
   if n==0:break
 pick(lambda r:r['event']=='COMPILATION' and r['cohort']=='PRIMARY_BASELINE' and bool(r['collapsed_parameter_values']) and r['collapsed_parameter_values']!='{}',4)
 pick(lambda r:r['event']=='COMPILATION' and r['job_id']=='selected-train-v1.F.003597b7b9c549df70c6')
 for prefix in ['dev-baseline-v1.F.3ea','selected-train-v1.F.098','main-order-17-v1.F.175','discovery-v2.F.5de','discovery-v2.F.7ac','discovery-v2.F.09a','control-order-17-v1.F.ce83','control-order-17-v1.F.8828']:
  pick(lambda r,prefix=prefix:r['event']=='RETRIEVAL_AND_BINDING' and r['job_id'].startswith(prefix))
 case_text=[]
 for i,r in enumerate(selected,1):
  if r['event']=='COMPILATION':
   evidence=f"来源验证：{r['source_validation_rejection'] or '通过'}；首个不能按既定映射对齐的动作：{r['first_unmatched_action'] or '无'}。逐位置对齐发现同名参数取值：{r['collapsed_parameter_values'] or '无'}。准入：{r['admitted']}（{r['admission_reason']}）。"
  else:evidence=f"绑定接受：{r['binding_accepted']}。原始解释：{r['binding_reason']}。实际直接动作 {r['actual_direct_actions']}，回退 {r['fallback']}；斜面首次公开可见位于动作 {r['late_plane_visible_before_step'] or '不适用/未标记'} 前。"
  case_text.append(f"### S{i:02d} `{r['job_id']}`\n\n事件 `{r['event']}`，来源 `{r['source_ref']}`。来源目标：{r['source_goal']}\n\n当前目标：{r['target_goal'] or '成功轨迹编译阶段'}\n\n模板：`{r['template_actions']}`\n\n{evidence}\n")
 skill=f'''# 成功技能复用瓶颈专项审计

主要基线独立统计：42 个成功轨迹产生42候选/42引导，27模板被来源验证拒绝，15模板通过，8获原生库准入。7个有效候选因同类型已有活跃且 utility≥0.5 的模板被拒；这是一类型一个模板的原生策略，不是每个新技能都会新增入库。其它组、敏感性和工程校准另见 root_cause_summary.json。

29次模板检索对应29次初始绑定请求，26拒绝、3接受。主 TEST F 12次模板检索全为斜面类型，0绑定接受；这12次在后续公开轨迹中全部出现斜面。初始拒绝有合理性：对象当时不在眼前；但 run_episode 仅启动时调用 bind_skill，后续执行循环不再检索/绑定。它解释了该实现中“后来满足可见性也不会进入L1”的机制，不证明重绑后一定能完成任务。

## 生成、来源验证与准入

27个拒绝中26个可通过逐位置重新匹配占位符对齐来源动作，{len(collapsed)}个在贪心匹配候选中出现同名参数对应不同字符串。这个静态诊断放宽的是来源对齐的参数一致性，不是执行安全检查；不能自动产生合格可迁移技能，也不能证明每一处字符串差异都要求不同对象参数。不同房间 hallway / greenhouse / outside 被压成同一个 room 是明确的表示风险；动物的不同称呼也可能是别名，或存在其它合法对齐。原拒绝的是给定example_bindings实例化后的序列，直接放宽来源检查不成立。另一例存在无法与来源动作序列对齐的字面/顺序问题。CSV字段 collapsed_parameter_values 保存的只是这项贪心诊断候选，不能作为自动错误裁定；S02是已通过来源验证却仍出现字符串差异的反例。

`ScienceCompiler` 要求模型生成 applicability，但构造 AlfWorldSkillTemplate 时没有保存该字段，运行绑定只看到模板/参数/示例值和当前公开状态。代码见 src/flowevo_sw/flowevo_adapter.py。丢失条件是可观察适配限制，实际效应尚未隔离。检索由上游 SkillLibrary 按精确 task_type 返回一个模板，不检查最少/最多摩擦、目标材料或新房间路线；同类相关不等于当前可用。

## 绑定之后仍存在什么问题

固定斜面模板 sw_9b4527b829af33c8 是 look at {{plane}} → connect block to {{plane}} → focus on {{plane}}。来源目标是 titanium/zinc 的最少摩擦，source episode selected-train-v1.F.003597b7b9c549df70c6 第1–5步完成。它保留了字面量 block，只参数化 plane，没有保存“如何在两个候选中选择”的实验/判断过程。来源反馈显示 terminal 连接，没有摩擦测量读数；成功评分并不证明该序列是完整科学实验。

免费 H1 对4个 TRAIN/DEV 状态枚举两块可见斜面，共8候选：6个被原 valid-action 检查拦在 connect block（当前物体为 brick）；另外2个可执行，选glass成功、选brass负分结束。因此“把绑定改晚”不足以修复：还涉及遗漏物体参数与把待判断答案提前塞进 plane 参数。不得从两块斜面的宿主得分挑赢的映射用于模型。这是诊断，不是8个新泛化测试。

有明确正确拒绝：未知物质/温度计不在当前房间，不能凭来源值填对象；最长/最短寿命技能不能照抄来源动物。在 control-order-17-v1.F.ce83a66e347b93d9a021 中，绑定 reason 明说从示例拿 chameleon egg，当前并未看到该动物，却被接受。这说明接受器只验证布尔值和参数非空，不验证每个映射的公开来源；不能把所有未执行都归为“过度保守”。该局先执行2个导航动作，随后在不可用动物动作前回退，避免强行错误目标。

## 治理记账的确定缺陷

batch_runner.publish_batch 在检索 best_layer==1 时无条件 record_template_usage(template_id, trace.success)，没有要求 direct_use_count>0。主要基线26个未进入直接路径的局仍给L1记了整局成功/失败，其他组55局同类。实际主要基线直接路径仅3次：非生物任务5动作直接成功，最短寿命TRAIN因已在outside在第一个导航动作前回退（0动作），范围外TEST先执行2动作后回退。不能用未执行模板的整局结果解释它的直接效用。主 TEST 期间80→92未到下一次20局周期审计，故不声称此错账已造成主TEST抑制或分数下降；它首先损害治理的归因可信度。

本轮另对6条真实主F记录执行同一M0库副本夹具：原 publish_batch 将 usage 从6变7，仅增加 direct_use_count>0 门控后保持6，见 root_cause_governance_fixtures.json。这是 LOCAL_COUNTERFACTUAL_SUPPORTED_ACCOUNTING_ONLY；不是整轮库演化或在线成绩回放。

## L2/L3 是否帮助或造成负迁移

确实使用了引导，未静默退化为空库。guidance_descriptive.csv 按任务类型区分引导/无引导，保留真实 holdout。主F只有2个无引导局，不能用跨阶段总成功率或删除提示词伪造因果对照。

明确的风险例：main-order-17-v1.F.36fece574b8499e3aace 检索了来源 70bab2789294b9804cf0 的引导，文字声称 focus 是 observe/measure friction，并建议对另一斜面重复 connect-and-focus；但 focus 有终止任务的语义。它是可见的不可靠指导内容，与模型本身已有误用竞争解释；尚不能证明这条指导诱发了该局错误。另一个引导正确提示先开门、再移动，动作中亦出现该次序，仍不能把一般常识重合算作因果帮助。

上游 L3 的位置统计解析器仍为 `take ... from ...`，ScienceWorld 多用 pick up/move，可能丢失位置抽取；这是接口适配不匹配，不等于已证明主要失败来自L3。需要先用免费解析器回放测试，不必先提出学习算法。

## 代表性案例（13个环节案例，来自12条独立轨迹，全部保留原记录 ID）

'''+ '\n'.join(case_text)
 (rep/'SKILL_REUSE_BOTTLENECK_ZH.md').write_text(skill)
 pairs=csvread('success_failure_pairs.csv')
 pairrows=[[r['task'],r['success_job'],r['failure_job'],r['first_action_divergence_step'],r['success_action'],r['failure_action']] for r in pairs]
 planning=f'''# 知识、规划、状态与适配的区分

主要基线有74失败局；59为官方负分结束。40/116局出现 focus 与 inspection/reveal/examine 等词同时出现的候选，其中31局失败。筛查词不能替代人工判断。具体反例：

- discovery-v2.F.20e65c56c84af8ab157f 第1步：目标red light bulb，却focus on red paint in cup；reason说这是最近的红色物体。公开反馈确认聚焦的是paint。这首先是对象落地和动作语义问题，不是不会搭电路的证据。
- discovery-v2.F.81f896325b22612a849e 第13–14步：看到ceramic cup后把杯子当ceramic inclined plane并focus，负分终止。说明名称/材质相近不代表目标实例相同。
- discovery-v2.F.1b4703786cd7f2ff0592 第45–46步：看见potato后称其为animal-like candidate，聚焦后失败。植物性食物是“动物”的论据明确错误；这是一个生物类别知识/目标匹配案例，不能外推为科学知识主导全部失败。
- discovery-v2.F.06eebbde9128242aba13 第10步及 discovery-v2.F.5de4ccea5ffbd8f8b877 第8步：reason最后都明确说green box，但JSON action却是red box。替换为保存reason中的动作，免费同前缀回放均完成。这是输出字段不一致，不是缺少正确颜色知识。解析器忠实执行action，没有错改模型答案。自动读取reason改action仍是待设计工程修复，本轮未部署。
- 未知物质案例还将10°C当前温度称为melting point；一次室温读数不等于熔点测量。即使该分支选green能过官方任务，也不证明实验设计正确。已成功轨迹也可能包含这类shortcut，成功编译不能以“整局成功”为唯一语义质量证据。
- discovery-v2.F.d99ba311a7e8ca9d2161 第99–100步：连接switch到battery两极时持续收到需要指定polarized contact points的反馈。这是接线接口/实验设计问题的直接证据，不足以断言模型不懂电学概念。

## 长程状态假设的反证约束

主要基线有{len(repeat)}个重复动作/相同可见上下文事件，{recent}个上一次同类反馈仍在最近16步范围内。特别是 find-plant 的3c034ff32bf35c264df7 与 find-living-thing 的ef2e54dbb3a42029c804，在最后两步重复卧室/走廊循环，reason仍称需要去bathroom。走廊公开出口没有bathroom，但有未访问邻室；不能手工假定存在直达浴室门。CF09–10仅用公开出口去未访问art studio，摆脱循环而分数不变，预算仍结束。

StateTracker 只保留最近16条完整反馈，更早仅动作，因此历史状态丢失是合理竞争假设；但短周期重复即使在16步内仍出现，不能把规划停滞全部归因于上下文截断，也不能据此声称加长记忆必有收益。公开view不是完整物理状态，不能将同look当成绝对同状态。

## 成功/失败配对

先列每类一对初始TRAIN成功/失败的最早动作差异，以便定位，再解释有意义的决策而不做跨variation因果归因：

{table(['任务','成功记录','失败记录','首个动作差异步','成功侧动作','失败侧动作'],pairrows)}

这些pair的目标参数或起始房间可能不同（完整字段见success_failure_pairs.csv）。斜面成功例5bfedeb6e825464e626d最终到达真正斜面，失败81f896325b22612a849e把杯子当目标；最早有解释意义的差异是目标对象验证，而不是机械地把第一步差异当原因。find-animal 成功6? 请以配对表真实ID为准：失败1b4703786cd7f2ff0592选择土豆，成功侧实际找到并转移动物，不能仅因成功访问了某房间就认定强制走同一路线能修复失败。熔点一对的差异还含阈值和颜色映射，必须使用各自目标。

本轮没有任何“离线删除技能提示后模型表现”的虚构实验。关于引导负迁移的净效应、记忆长度净效应以及科学知识不足在总体中的因果占比，均为 INSUFFICIENT_EVIDENCE。
'''.replace('find-animal 成功6? 请以配对表真实ID为准：','find-animal 的配对中，')
 (rep/'PLANNING_KNOWLEDGE_STATE_AUDIT_ZH.md').write_text(planning)
 cfrows=[[r['case_id'],r['hypothesis'],r['job_id'],r['prefix_len'],r['factual_score'],r['alternative_score'],r['alternative_blocked'] or '无'] for r in cf]
 causal=f'''# 免费最小反事实诊断

冻结计划见root_cause_counterfactual_plan.json；18个检查点/映射案例、36条本地JVM分支，来自14个独立TRAIN/DEV轨迹。所有分支reset，逐步重放来源前缀并核对公开哈希，再执行最多3个已确定动作；有些只剩2步。没有TEST回放、没有新模型规划、没有Gold。完整动作/反馈/宿主结果见minimal_counterfactuals.csv与receipts。

{table(['案例','假设','来源','前缀动作数','事实分支最终分','替代分支最终分','原直接执行检查阻断动作'],cfrows)}

H1：8个晚绑定候选中6个因字面block无法对应brick被原有效动作接口阻断，另2个同状态选不同斜面得到100和-100。**否定“仅延后绑定就足够”**，支持对象参数覆盖与答案选择缺口。初始拒绝本身合理，暴力放宽不是修复。唯一成功替代不是可部署的参数选择器，不能挑它报泛化收益。

H2：6个同对象focus→look at在相同前缀均避免当步负分，0个完成任务；另2个只执行原reason已经写出的green box动作，均完成。这只证明两个给定动作替换的效果，不证明模型在新提示/新解析下会自然产生该动作，也不证明8例代表总体。

H3：2个局部路线替换均进入未访问房间，分数未变且最终预算结束。说明现有动作预算内有可执行的探索分支，但未验证到达目标或整局收益，也未隔离状态遗忘与规划策略。

证据等级：环境原反馈/代码执行事实为 OBSERVED_ERROR；上游机制解释为 PLAUSIBLE_CAUSE；相同前缀的动作替换结果为 LOCAL_COUNTERFACTUAL_SUPPORTED；模型在修复后的行为、完整新任务收益为 NOT_VERIFIED。CSV的LOCAL_COUNTERFACTUAL_SUPPORTED只表示分支发生不同可见后果，绝不意味着正向收益。

计划构建阶段先发现“走廊可直达浴室”的诊断者假设与公开look不符，改为不假定目标路线的未访问邻室测试；均发生在成功写出计划及执行分支之前。第一次进程池启动因函数名被字符串遮蔽而未执行，修复后按同一冻结计划执行。技术失败不产生收费请求，不是挑分支重跑。

另有6个纯Python治理夹具：每条真实主F记录各自从同一M0出发，比较原记账函数与仅在实际直接执行时记账的门控，前者usage均加1、后者均不变。该结果只支持信用更新差异，不属于上述36条JVM分支，也不证明历史准入/抑制或最终成绩变化。

没有继续追加block→brick后看哪个映射赢的尝试，也没有修改原runtime。逐位置来源参数重绑属于另一个静态工程检查，26/27拒绝候选可对齐来源，并不等同于26个自然可用技能。
'''
 # Count distinct sources rather than handcount repeated plane mappings.
 causal=causal.replace('来自14个独立TRAIN/DEV轨迹',f"来自{len({r['job_id'] for r in cf})}个独立TRAIN/DEV轨迹")
 (rep/'CAUSAL_DIAGNOSTICS_ZH.md').write_text(causal)
 decision='''# 下一轮研究决策（至多三个问题）

**当前证据不足以支持提出新的 FlowEvo 扩展算法。** 应先修复和验证接口/归因问题；不继续生成失败算子，不执行阶段 B。本轮下列最小核验均可0 API、0元完成，未来若要观察模型在新提示下的后续决策，需要另行申请，不能把这里当付费授权。

|排序|问题|证据强度|影响范围|最小改变/可修复性|研究独立性|
|---|---|---|---|---|---|
|1|成功技能表示与一次性绑定不匹配探索任务|OBSERVED_ERROR/LOCAL_COUNTERFACTUAL_SUPPORTED，整局收益NOT_VERIFIED|主F 12检索来自6独立TEST variation；4TRAIN/DEV状态8局部映射|先检查block等硬编码参数、保留applicability、在状态可见时重新评估；不放松目标证据|条件技能表达可能是能力缺口，但当前适配与编译缺陷尚未排除|
|2|focus动作语义、对象落地及reason/action不一致|6例局部存活、2例既有reason动作完成，LOCAL_COUNTERFACTUAL_SUPPORTED|6+2个独立TRAIN variation，知识/任务类型不止一种|先做动作语义说明和字段一致性工程检查|首先是基础模型/接口契约问题，未证明要新学习算法|
|3|未执行模板被计入直接效用|OBSERVED_ERROR；6个夹具LOCAL_COUNTERFACTUAL_SUPPORTED_ACCOUNTING_ONLY|主要基线26条、其它组55条；不是独立81任务|仅实际直接执行时记直接信用；引导与整局信用另记|普通适配工程Bug，不能包装创新|

## 1. 表示和绑定

竞争解释：初始拒绝可能完全正确；晚时刻即使对象可见，也仍缺科学比较过程、正确目标选择或物体实例。反证：在新对象全可见时，现有模板经公开信息的唯一映射即可跨实例稳定执行，且补全参数/重绑没有新增机会，则当前表示瓶颈解释应弱化。免费最小下一步是对保存轨迹静态检查每个固定对象字面量、参数来源及前提，再在同一已保存TRAIN/DEV前缀运行固定映射对照；请求0、费用0。不得用替代分支的评分挑映射。是否需要新算法：尚不成立，先测简单参数化和时机修复。

## 2. 动作语义与字段一致性

竞争解释：模型本身在压力下猜测、目标对象理解错误、成功引导中也传播了错误focus用法。反证：免费回放中look at也在同一前缀立即失败，或日志中的reason/action实际上同义无冲突，会推翻对应局部解释；本轮这8例没有出现该反证。下一步先编写不调用模型的接口说明/一致性检测器，验证只报警、不偷偷改答案，并用现有原始响应核对误报；请求0、费用0。检测通过仍不证明新模型决策改善，若要做提示改动的闭环试验，阶段B需独立费用申请和批准。是否需要新算法：暂无证据。

## 3. 治理信用

竞争解释：原作者可能想记录“检索后的整局utility”，但目前字段/准入把它解释为模板效用，且没有区分直接与引导贡献。反证：记录器已有其他门控能阻止这些26次调用，或usage实际不影响准入/抑制，则此缺陷解释需撤回；源码及6个M0夹具显示没有该门控，原函数会更新成功率。下一步可对完整历史库按真实trace顺序做归因敏感性检查，区别于本轮已完成的单事件夹具，0请求、0元；不重新评分或声称模型后续行为不变。是否需要新算法：不需要。

长程状态/科学知识作为主要瓶颈均不进入前三的独立算法立项。重复中的不少反馈仍在最近16步；新路线局部可行不代表记忆模型会选择它。科学错误有个例，成功轨迹也可能靠终点猜测，没有充分因果覆盖。没有正式阶段 B 费用申请，也没有任何已授权的人民币5–10元额度。
'''
 (rep/'NEXT_RESEARCH_DECISION_ZH.md').write_text(decision)
 rootreport=f'''# FlowEvo–ScienceWorld 根因诊断：阶段 A

结论：**先修正技能表示/绑定接口、动作语义和治理记账；当前证据不足以支持提出新的 FlowEvo 扩展算法。** 没有把原有低分概括为“科学知识不够”，也没有把绑定拒绝全部视为错误。

{scope}

## 主要发现

1. **技能供给损失与使用时机是具体可定位的问题。** 基线42成功编译候选中27被来源验证拒绝，15通过、8准入；26个拒绝可在逐位置放宽参数一致性后对齐来源，提示同名参数混用/映射错误，但原拒绝正确。主F的12个模板检索均初始拒绝，后续都见到斜面，代码却不重绑。免费晚绑定8候选中6个被未参数化的block阻断，另两个选择不同斜面一胜一负，说明单独放宽绑定不成立。证据：OBSERVED_ERROR及LOCAL_COUNTERFACTUAL_SUPPORTED；整局算法收益NOT_VERIFIED。
2. **大量候选涉及focus被当成观察、错误对象及输出不一致。** 40/116局出现检查性focus语言，31局失败，仅作为候选筛查。6个公开对象相同的look替换避免即时负分但未完成；2例reason写green、action写red，按既有reason替换后完成。证据支持局部执行选择问题，不能证明改善提示后模型会自动修复，也不能外推总体科学能力。
3. **治理错把未执行模板归入整局信用。** 主要基线26条记录，其他组55条，直接路径未进入仍记usage/success。它是可复现工程归因缺陷，不是新算法成果。不能据此声称已导致本轮主TEST失分。

L2/L3确有真实引导，部分内容把focus描述为观察摩擦，存在负迁移风险；但原模型的动态轨迹已出现同类误用，现有少量holdout不足以识别引导的净效应。长程记忆截断也未被隔离：重复可见动作{len(repeat)}次，其中{recent}次前次反馈仍在16步内，不能自动归因于长程遗忘。

## 数据与证据等级

{table(['总体','轨迹','成功','失败','动作'],cohortrows)}

全部模型请求/Token均从旧记录读取，费用列是历史调用量，不是本轮新增费用。因果标签严格区分观察错误、合理解释、局部动作替代支持和未验证的在线效果。全部18个免费对照在TRAIN/DEV进行，36分支前缀哈希一致。2个动作替换完成任务不是重新取得的模型成绩，不能加到历史成功率中。

## 交付与复算

- [失败分类](FAILURE_TAXONOMY_ZH.md)：252局数据库，终止/中间错误/上游根因分层。
- [技能链路与代表性案例](SKILL_REUSE_BOTTLENECK_ZH.md)：{len(selected)}个具体案例及候选/检索明细。
- [知识、规划和状态](PLANNING_KNOWLEDGE_STATE_AUDIT_ZH.md)：逐步证据、成功失败配对与不可归因之处。
- [局部反事实](CAUSAL_DIAGNOSTICS_ZH.md)：全部18案例，含无效及负面结果。
- [至多三个后续问题](NEXT_RESEARCH_DECISION_ZH.md)：可证伪条件、工程优先和0元最小核验。
- [零API复算步骤](ROOT_CAUSE_REPRODUCE.md)。输入manifest、规则说明、运行回执和CSV均随分支提供，历史报告/运行时/评分脚本未改。

**新增 DeepSeek API 调用：0。新增 API 费用：0 元。阶段 B：未执行。**
'''
 (rep/'ROOT_CAUSE_AUDIT_ZH.md').write_text(rootreport)
 (out/'artifacts/root_cause_report_metrics.json').write_text(js({'primary_negative_terminal':len(negative),'negative_terminal_after_focus_feedback':focus_end,'primary_visible_repeat_events':len(repeat),'repeat_events_with_prior_feedback_in_last16':recent,'collapsed_parameter_rejections':len(collapsed),'skill_cases':len(selected),'counterfactual_cases':len(cf),'counterfactual_unique_source_episodes':len({r['job_id'] for r in cf})}))
 print('Wrote six Chinese reports; no model calls')
if __name__=='__main__':main()
