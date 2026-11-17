"""Chinese engineering findings; no new task success-rate estimate."""
import argparse,collections,csv,json
from pathlib import Path
from engineering_common import read,write

def table(headers,rows):
    clean=lambda x:str(x).replace('|','/').replace('\n',' ')
    return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(clean,row))+'|' for row in rows])
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve();out=root/'output';art=out/'artifacts/engineering';res=out/'results/engineering';rep=out/'reports'
    def rows(name):
        with (res/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
    gov=read(art/'governance_receipt.json');action=read(art/'action_audit.json')['summary'];binding=read(art/'binding_summary.json')
    events=rows('governance_events.csv');deltas=rows('governance_template_deltas.csv');structures=rows('skill_representation_audit.csv');bindings=rows('conditional_binding.csv')
    final=[r for r in events if r['mode']=='chained_credit_and_age_fix'];changes=[r for r in final if r['admission_changed']=='True']
    summaries=gov['summary'];sr=[[r['run'],r['arm'],r['mode'],r['templates_changed'],r['admission_changes'],r['retrieval_mismatches']] for r in summaries]
    changed_F=[r for r in deltas if r['mode']=='chained_credit_and_age_fix' and r['arm']=='F' and r['changed']=='True']
    dr=[[r['run'],r['template_id'],r['task'],r['original_template_utility'],r['recomputed_template_utility'],r['original_template_use_count']+'→'+r['recomputed_template_use_count'],r['original_template_status']+'→'+r['recomputed_template_status']] for r in changed_F]
    ar=[[r['run'],r['arm'],r['job_id'],r.get('candidate_template_id','see compilation source'),r['original_admitted']+'→'+r['recomputed_admitted'],r['first_retrieval_divergence']] for r in changes]
    governance=f'''# 治理信用和库状态重算

本轮没有调用模型，也没有重新计算或报告任务成功率。冻结的动作、模型输出、编译候选和任务结果均作为外生历史记录。原发布器从冻结Git对象原样提取，先验证再作信用干预。

## 口径与生产代码修复

- **直接信用**：至少执行一个 direct_skill 动作才进入直接使用计数。仅当最后一个直接动作的宿主结果已完成任务，才记直接完成；需要回退的部分执行记不完整尝试，后续动态成功不归给模板。零动作的进入/阻断另记，不计使用。
- **引导信用**：按实际 skill_guided 动作记曝光及整局结果的关联。L2与L3可以同时注入，分别记共同曝光，但原生任务级 guided_total 每局只加一次。不能把共同曝光拆成两个独立因果收益。
- **仅检索**：只记 retrieved / retrieved_only，没有任务结果效用。引导未实际注入时也只算检索。
- 纯holdout需要有动态动作，且没有直接前缀、没有引导动作。混合路径单列。
- 修正后使用 ScienceSkillLibrary 序列化上述账本，batch_runner.publish_batch 已接入；三层检索、直接路径、引导、回退及原生治理阈值仍保留。

没有实际直接使用时，上游 template_utility 初始值仍为1。这是原有准入先验，**不是测得的100%成功率**。本轮没有另造效用学习算法来改善这一先验。

## 重算范围和对照

{len(gov['reference_batches_reproduced_exactly'])}个批次、236条正式轨迹的原库状态及发布事件逐项复现。16条discovery-v1工程校准的contrastive_stats无法由最终冻结发布器复现，单列排除库状态因果重算；这些轨迹仍包含在动作响应审查中。没有按结果好坏挑选正式任务。

1. isolated_credit_fix：每个run从原初始库独立修正当前阶段信用，暖库旧错账尚在。
2. chained_credit_fix：从空库重新走TRAIN发布顺序，再按原计划独立分叉，修正信用但保留原闲置计时。
3. chained_credit_and_age_fix：在上一项基础上修正新入库技能的闲置起点，作为本分支默认实现。

仅去掉检索计数，会暴露原先的闲置计时缺陷：未使用模板没有last_used时，旧审计按第0局起算，新入库技能可能立即被判长期闲置。现在记录独立admitted_at；第一次实际使用之前按入库时间计龄，不伪造一次使用。原50局阈值不变。旧库缺失入库时间时不猜测；完整链式重算才有真实发布时刻。

{table(['run','组','重算模式','最终变化模板数','准入变化事件','检索与旧轨迹不相容'],sr)}

完整修正分支中有{len(changes)}个准入判定变化事件，下面列出全部。**一旦检索不同，后续保存的响应就不能被当作新策略的自然行为。** 重算可以说明在固定历史观察下的库记账/准入/抑制差异，不能说明真实在线任务结果会怎样变化。

{table(['run','组','来源记录','候选模板ID','原→重算准入','首次检索分歧'],ar)}

## F组具体效用和抑制差异

{table(['阶段','模板ID','任务类型','原效用','重算效用','原→重算使用数','原→重算状态'],dr)}

其它组及所有模式的逐模板变化见 results/engineering/governance_template_deltas.csv；逐事件审计见governance_events.csv；完整库状态见artifacts/engineering/governance_states.json。ABSENT/空值表示该版本库中不存在，不补成效用0。没有出现引导负迁移抑制的新证据；该原生判据保留，但曝光关联不等于净因果收益。
'''
    (rep/'GOVERNANCE_ENGINEERING_ZH.md').write_text(governance,encoding='utf-8')
    examples=rows('action_wording_examples.csv');regressions=rows('action_regression_cases.csv')
    audit=f'''# 动作接口一致性：只报警

审查全部{action['responses']}条已有action响应，其中7438条对应实际执行动作，253条未进入实际动作序列。没有发起新请求。143条旧格式请求无法恢复结构化公开上下文，标为LEGACY_FORMAT_UNSUPPORTED，不当作新接口错误；其余输入来自当时的请求公开状态。检测器不读取动作后反馈、score、reward或Gold。

|类别|最终筛查数量|解释|
|---|---|---|
|明确reason/action冲突|{action.get('REASON_ACTION_CONFLICT',0)}|最终显式修正写green box，action仍red box|
|明确目标类型矛盾|{action.get('TARGET_OBJECT_MISMATCH',0)}|例如把cup当inclined plane、paint当light bulb|
|材质名/对象别名仍不确定|{action.get('TARGET_REFERENCE_AMBIGUOUS',0)}|wood等短称不能仅凭词面宣布不是斜面别名|
|focus作为检查的语言候选|{action.get('FOCUS_AS_INSPECTION',0)}|需人工复核，不能全当确证错误|
|其它动词语义差异候选|{action.get('ACTION_SEMANTICS',0)}|仅警告，不自动替换动作|
|明确正常措辞差异|{action.get('relation:NORMAL_WORDING_VARIANT',0)}|冠词、公开房门称呼等|
|可能是中间导航步骤|{action.get('relation:POSSIBLE_INTERMEDIATE_ROUTE',0)}|先去走廊不等于与最终浴室目标矛盾|

这是候选筛查，不是经过独立标注集验证的准确率、召回率或整体知识错误比例。开发时发现代词、泛称animal和中间导航造成误报，已加入回归约束。生物类别知识（如把potato当animal）仍不是字面接口检查能可靠裁定的范围，明确保留漏检/UNKNOWN。

## focus契约与不干预验证

focus可能推进子目标、完成任务或在错误选择时终止任务；它不是通用观察/测量动作。First focus on thermometer等明确要求仍然合法。共审查{action['focus_responses']}个focus响应，没有设置focus禁令。

新ActionGateway只把interface_audit写入日志。它不改action，不发VETO，不进入重规划提示，也不增加请求。12个TRAIN/DEV真实JVM检查涵盖已知错误、必需focus和正常表述；均重放同一公开前缀并保持原动作与动作后公开哈希一致。错误动作也原样执行，不能把报警误称为已经修复模型决策。

{table(['来源','步','人工参照类别','检测到该类别'],[[x['job_id'],x['step'],x['reference_review'],x['flagged']] for x in regressions])}

以下为按记录ID排序选取的正常措辞样例，不是随机性能测试：

{table(['请求ID','实际action','保存reason'],[[x['request_id'],x['action'],x['reason']] for x in examples])}

完整逐响应表为results/engineering/action_response_audit.csv，保留原请求ID、实际执行标记、公开输入哈希和警告证据。
'''
    (rep/'ACTION_INTERFACE_ENGINEERING_ZH.md').write_text(audit,encoding='utf-8')
    repairs=[x for x in structures if x['repair_status']=='SOURCE_VALID_CANDIDATE']
    full=[x for x in bindings if x['preparation_only']=='False'];prefix=[x for x in bindings if x['preparation_only']=='True']
    representation=f'''# 技能表示与条件绑定：简单修正的边界

覆盖全部96条正式基线TRAIN/DEV历史轨迹（含8条重复TRAIN敏感性，不能算新独立任务）。其中34个已保存编译输出通过当前真实ScienceCompiler的缓存路径重新做来源验证，**没有向模型重新生成技能**。13个原候选通过来源验证；21个不通过。只在来源动作的参数对齐唯一时拆分同名参数，得到5个严格来源有效的修正候选；15个多重对齐和1个无法对齐保留拒绝。不能把不同字符串自动当不同对象，尤其可能存在别名。

{table(['来源','任务','原→修正来源有效','修正细节'],[[x['job_id'],x['task'],x['original_source_valid']+'→'+x['repaired_source_valid'],x['repair_details']] for x in repairs])}

编译器生成的applicability原文保留在ScienceSkillTemplate，穿过入库、序列化、加载和检索；同时单列房间/导航、实验对象、仪器、搬运目标和最终选择角色。6个M0模板从保存编译输出恢复条件，原动作、效用、准入和状态不变。5个修正候选没有自动入库。

## 条件绑定检查

在15条实际检索过模板的TRAIN/DEV轨迹上，预先选初始状态和第一次公开出现斜面的状态。枚举公开候选，不按宿主得分选赢家。最终共{len(bindings)}个映射/表示检查，**不是{len(bindings)}条任务**；其中完整模板{len(full)}个、准备片段{len(prefix)}个。

条件验证器为三值逻辑：FALSE拒绝、UNKNOWN弃权，只有全部有公开证据才ALLOW。当前只覆盖有界条件语法；其它原文条件完整保留但不默认为真。类别和目的地内容未被证实时仍未知。即使接口允许connect agent/air/wire，也不证明这些实体能替代源实验对象；参数化一个字面量不等于证明角色可交换。

{table(['判定','候选数'],sorted(binding['binding_verdicts'].items()))}

完整模板ALLOW数为{sum(x['accepted']=='True' for x in full)}。准备片段ALLOW数为{sum(x['accepted']=='True' for x in prefix)}，去重后仅2个真实JVM分支、同一DEV公开状态。它们可以分别观察并连接两块斜面；环境反馈仍是terminal连接，未给出摩擦比较结论。最终focus选择被明确保留为未知，未执行目标选择。**这只恢复了局部可执行性，没有恢复完整技能迁移，也没有证明实验科学性。**

该验证器是可调用的离线诊断接口，没有接管线上bind_skill或通过全面拒绝来重做基线。原因是条件解析覆盖和实验结果解释尚未得到充分验证。原模型绑定会收到新增保留的条件，但本轮没有调用它，不能声称新的自然绑定行为改善。当前源验证和每步valid-action守卫均未放宽。

## 工程过程与可证伪边界

首次结构探查发现底层to_dict返回可变列表，诊断参数提升会误改原模板对象；现已使用独立深拷贝并增加隔离回归测试。binding_plan.json保留为已废弃的探查计划；最终使用binding_plan_v2.json，全部候选重新计算。没有据得分挑映射、删除负例或继续尝试目标答案。

可推翻“这些简单修正已足够”的证据已存在：完整技能仍缺可证明的目标选择；许多来源对齐仍不唯一。但不能反过来声称新算法必要，因为大部分自然语言条件仍不能被第一版验证器完整解释。下一步仍可免费扩充条件覆盖、审查角色约束和科学测量契约；现有数据不足以证明它们能解决大部分任务问题。
'''
    (rep/'SKILL_REPRESENTATION_ENGINEERING_ZH.md').write_text(representation,encoding='utf-8')
    report=f'''# 工程修复与机制证伪（零API）

结论：三类工程工作已完成，并得到有限且可复查的改进；**没有证据表明简单修正已恢复大部分完整技能迁移，也没有足够证据提出新算法。** 本轮不重新报告任务成功率。

1. 治理：直接执行、L2/L3实际引导及仅检索曝光分账，修正入库前闲置时间误计。42个历史批次/236条正式轨迹原状态精确复现，再作三种记账重算。库效用、准入及抑制确实改变，但检索分歧后的旧响应不是新策略输出。
2. 接口：审查{action['responses']}条保存响应；最终有2条明确reason/action冲突、4条明确目标类型矛盾，另有候选和UNKNOWN。检查器只记录警告，12个真实JVM一致性检查证明动作和公开反馈不变；不禁用focus。
3. 表示：保留适用条件及角色；21个来源拒绝中5个经唯一对齐修复，其余保留拒绝。{len(bindings)}个绑定/表示候选中没有完整技能被证明可迁移；4个准备候选对应2个去重JVM片段，仅证明局部可执行。

生产代码实际改动是治理分账、入库时间、元数据保留和只报警日志。结构修复候选及条件绑定仍是离线诊断，不自动准入、不更改原历史结果。全部JVM检查只用TRAIN/DEV，未重跑TEST求解。

- [治理细节、具体模板ID及准入变化](GOVERNANCE_ENGINEERING_ZH.md)
- [动作分类、正常措辞与focus](ACTION_INTERFACE_ENGINEERING_ZH.md)
- [表示修正、条件绑定与负结论](SKILL_REPRESENTATION_ENGINEERING_ZH.md)
- [可复算步骤](ENGINEERING_REPRODUCE.md)

证据回执、完整CSV、库状态和测试均在本分支。服务器只开放loopback的网络命名空间执行；FLOWEVO_OFFLINE_ONLY额外阻止模型客户端构造和请求。运行前后历史账本仍为8941次，原输入哈希未变，最终回执见artifacts/engineering/verification.json。

**本轮新增DeepSeek/其它付费模型调用0次，新增API费用0元。没有阶段B付费实验。**
'''
    (rep/'ENGINEERING_REPORT_ZH.md').write_text(report,encoding='utf-8')
    write(art/'report_metrics.json',{'formal_publications_replayed':236,'reference_batches':42,'admission_changes_final_mode':len(changes),
        'action_responses':action['responses'],'full_binding_allowed':sum(x['accepted']=='True' for x in full),'preparation_binding_allowed':sum(x['accepted']=='True' for x in prefix),
        'new_model_calls':0,'new_api_cost_cny':0})
    print('Wrote four Chinese engineering reports; no model calls')
if __name__=='__main__':main()
