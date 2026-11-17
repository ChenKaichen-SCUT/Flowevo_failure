"""Generate descriptive audit tables from frozen human-style assistant reviews.

No label inference, task runner, model request or outcome recomputation occurs here.
"""
import argparse, collections, csv, json
from pathlib import Path
from success_audit_prepare import read, write, sha, verify_frozen
from success_audit_compile import csv_write

TEMP = 'discovery-v2.F.2beaa66b5bcd3db3dc64'
MELT = 'discovery-v2.F.6aebd9fb1322c1074fb6'

def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

def main():
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True); a = p.parse_args()
    out = Path(a.output).resolve(); art = out/'artifacts/success_audit'
    verify_frozen(out, read(art/'source_review_freeze.json')['files'])
    inventory = read(art/'success_inventory.json')
    source = {r['job_id']: r for r in read(art/'source_adjudicated.json')}
    chain = {r['job_id']: r for r in read(art/'compilation_chain.json')}
    review = {r['job_id']: r for r in read(art/'compilation_review_b.json')}
    assert set(source) == set(chain) == set(review)
    assert all(r['source_label'] == source[jid]['label'] for jid, r in review.items())
    primary = [r for r in inventory if r['scope'] == 'PRIMARY_TRAIN_DEV']
    supplementary = [r for r in inventory if r['scope'] == 'SUPPLEMENTARY_TRAIN_VERSION']
    assert len(primary) == len({r['unit'] for r in primary}) == 31
    assert sum(source[r['job_id']]['requires_inference_or_experiment'] for r in primary) == 20
    metrics = collections.Counter(source[r['job_id']]['label'] for r in primary)
    assert metrics == {'PROCESS_SUPPORTED': 2, 'PARTIALLY_SUPPORTED': 2,
                       'ANSWER_WITHOUT_OBSERVED_SUPPORT': 17, 'PROCESS_NOT_REQUIRED': 10}
    supported = [r['job_id'] for r in primary if source[r['job_id']]['label'] == 'PROCESS_SUPPORTED']
    assert set(supported) == {TEMP, MELT}
    # These step sets are explicit scientific/goal-marker annotations, not keyword detection.
    core = {TEMP: [9, 14], MELT: [5, 6, 7, 8, 9]}
    complete = {TEMP: [1, 9, 14, 17], MELT: [5, 6, 7, 8, 9]}
    core_kept = {jid: set(steps) <= set(chain[jid]['exact_source_alignment_1based'] or []) for jid, steps in core.items()}
    full_kept = {jid: set(steps) <= set(chain[jid]['exact_source_alignment_1based'] or []) for jid, steps in complete.items()}
    def joint(r):
        x, y = r['parameter_roles_preserved'], r['applicability_supported_by_source']
        return False if x is False or y is False else True if x is True and y is True else None
    joint_counts = collections.Counter(encoded(joint(review[r['job_id']])) for r in primary)
    role_counts = collections.Counter(encoded(review[r['job_id']]['parameter_roles_preserved']) for r in primary)
    condition_counts = collections.Counter(encoded(review[r['job_id']]['applicability_supported_by_source']) for r in primary)
    comparisons = [r for r in primary if source[r['job_id']]['comparison_required']]
    missing_decision = [r for r in comparisons if not source[r['job_id']]['decision_supported']]
    observed_links = [r['job_id'] for r in primary if source[r['job_id']]['observed_decision_dependency']]
    assert observed_links == [TEMP] and len(comparisons) == 19 and len(missing_decision) == 18
    classes = {}
    for r in inventory:
        jid = r['job_id']
        if jid not in source: classes[jid] = 'NOT_AUDITED_TEST'
        elif jid == MELT: classes[jid] = 'A_SOURCE_METHOD_RETAINED_STRUCTURAL_CANDIDATE'
        elif jid == TEMP: classes[jid] = 'B_L1_LOSS_L2_RULE_RETAINED'
        elif source[jid]['comparison_required'] and not source[jid]['decision_supported']:
            classes[jid] = 'C_SOURCE_DECISION_EVIDENCE_INCOMPLETE'
        elif source[jid]['label'] == 'PROCESS_SUPPORTED':
            classes[jid] = 'SUPPLEMENTARY_METHOD_WITH_NAVIGATION_LOSS'
        else: classes[jid] = 'D_SIMPLE_OR_PARTIAL_STATE_CASE'
    rows = []
    source_csv = {r['job_id']: r for r in csv.DictReader((out/'results/success_trace_audit.csv').open(encoding='utf-8', newline=''))}
    for item in inventory:
        jid = item['job_id']; s = source.get(jid); c = chain.get(jid); r = review.get(jid)
        row = {k: item[k] for k in ('job_id', 'episode_id', 'task', 'variation', 'unit', 'run', 'arm', 'split', 'scope')}
        row.update(source_ref=item['source_ref'], source_sha256=item['source_sha256'],
                   source_original_sha256=source_csv[jid]['source_original_sha256'],
                   episode_semantic_sha256=item['episode_semantic_sha256'],
                   historical_host_success_confirmed=True, source_process_label=s['label'] if s else 'NOT_AUDITED_TEST',
                   audit_class=classes[jid], evidence_grade=s['evidence_grade'] if s else 'HISTORICAL_METADATA_ONLY',
                   critical_steps_1based=encoded(s['critical_steps']) if s else '',
                   measurement_steps_1based=encoded(s['measurement_evidence_steps']) if s else '',
                   comparison_steps_1based=encoded(s['comparison_evidence_steps']) if s else '',
                   final_selection_steps_1based=encoded(s['selection_steps']) if s else '',
                   source_decision_supported=s['decision_supported'] if s else None,
                   observed_decision_dependency=s['observed_decision_dependency'] if s else None,
                   source_process_reason_zh=s['reason_zh'] if s else 'TEST仅库存，不审阅过程或设计技能',
                   compiler_request_ref=c['compiler_request_ref'] if c else '',
                   compiler_request_sha256=c['compiler_request_sha256'] if c else '',
                   compiler_response_ref=c['compiler_response_ref'] if c else '',
                   compiler_response_sha256=c['compiler_response_sha256'] if c else '',
                   actual_compiler_input_all_public_steps=c['compiler_input_equal_to_all_public_steps'] if c else None,
                   saved_reason_in_compiler_input=c['source_reason_sent_to_compiler'] if c else None,
                   raw_action_template=encoded(c['raw']['action_template']) if c else '',
                   raw_parameters=encoded(c['raw']['parameters']) if c else '',
                   raw_example_bindings=encoded(c['raw']['example_bindings']) if c else '',
                   raw_applicability=c['raw'].get('applicability', '') if c else '',
                   raw_rules=encoded(c['raw'].get('rules', [])) if c else '',
                   saved_compilation_file_present=source_csv[jid]['compilation_file_present'],
                   historical_source_valid=source_csv[jid]['historical_source_valid'],
                   historical_rejection=source_csv[jid]['historical_rejection'],
                   current_cached_source_validation=c['current_cached_source_validation'] if c else None,
                   current_cached_rejection=c['current_cached_rejection'] if c else '',
                   exact_source_alignment_1based=encoded(c['exact_source_alignment_1based']) if c else '',
                   key_step_fidelity=r['key_step_fidelity'] if r else 'NOT_AUDITED_TEST',
                   source_supported_core_steps_retained=core_kept.get(jid),
                   source_supported_required_markers_retained=full_kept.get(jid),
                   parameter_role_fidelity=r['parameter_role_fidelity'] if r else '',
                   parameter_roles_preserved=r['parameter_roles_preserved'] if r else None,
                   applicability_supported_by_source=r['applicability_supported_by_source'] if r else None,
                   roles_and_conditions_supported=joint(r) if r else None,
                   condition_fidelity=encoded(r['condition_fidelity']) if r else '',
                   raw_applicability_retained_in_historical_L1=c['original_applicability_in_historical_L1'] if c else None,
                   raw_applicability_retained_in_A2_roundtrip=c['A2_applicability_preserved'] if c else None,
                   L1_decision_fidelity=r['l1_decision_fidelity'] if r else '',
                   L2_decision_fidelity=r['l2_decision_fidelity'] if r else '',
                   raw_rules_equal_saved_L2=c['raw_rules_equal_historical_L2'] if c else None,
                   L2_claims_unobserved_experimental_effect=r['l2_claims_unobserved_experimental_effect'] if r else None,
                   L2_unobserved_effect_rule_indices=encoded(r['l2_unobserved_effect_rule_indices']) if r else '',
                   information_losses_zh=encoded(r['losses_zh']) if r else '',
                   retained_information_zh=encoded(r['retained_zh']) if r else '',
                   unsupported_additions_zh=encoded(r['unsupported_additions_zh']) if r else '',
                   attribution_scope_zh=encoded(r['attribution_scope_zh']) if r else '',
                   historical_admission_events=source_csv[jid]['historical_admission_events'],
                   historical_lifecycle=source_csv[jid]['lifecycle'],
                   full_transfer_demonstrated=False if s else None,
                   review_ref='artifacts/success_audit/compilation_review_b.json#'+jid if r else '')
        rows.append(row)
    csv_write(out/'results/skill_information_loss.csv', rows)
    summary = {
        'primary_units': 31, 'source_reviewed_records': 39, 'historical_success_records': len(inventory),
        'supplementary_records': len(supplementary), 'supplementary_new_units': len({r['unit'] for r in supplementary}-{r['unit'] for r in primary}),
        'historical_TEST_metadata_records': 63, 'source_labels_primary': dict(metrics),
        'class_counts_primary': dict(collections.Counter(classes[r['job_id']].split('_')[0] for r in primary)),
        'process_supported': {'numerator': 2, 'denominator_all_primary': 31, 'denominator_inference_or_experiment': 20},
        'insufficient_observed_decision': {'numerator': 18, 'denominator_comparison_required': 19, 'denominator_all_primary': 31},
        'core_operations_retained': {'numerator': sum(core_kept.values()), 'denominator': 2, 'annotated_steps': core},
        'required_completion_markers_retained': {'numerator': sum(full_kept.values()), 'denominator': 2, 'annotated_steps': complete},
        'parameter_roles_primary': dict(role_counts), 'conditions_source_consistent_primary': dict(condition_counts),
        'roles_and_conditions_joint_primary': dict(joint_counts),
        'decision_dependency': {'denominator': 1, 'source_jobs': observed_links, 'L1_executable_branch_retained': 0, 'raw_L2_text_retained': 1},
        'structural_method_candidates': [MELT], 'complete_transfers_demonstrated': 0,
        'primary_cached_source_valid': sum(chain[r['job_id']]['current_cached_source_validation'] for r in primary),
        'primary_L2_unobserved_experimental_effect': sum(review[r['job_id']]['l2_claims_unobserved_experimental_effect'] for r in primary),
        'new_task_success_rates_reported': False, 'new_model_API_calls': 0, 'new_API_cost': 0,
        'manual_review_warning': 'Frozen assistant annotations, not independent human accuracy estimates; unknown is not false.',
        'denominator_warning': 'Descriptive census of this successful TRAIN/DEV corpus; not a random population sample or new success-rate experiment.',
        'compilation_review_b_sha256': sha((art/'compilation_review_b.json').read_bytes())}
    assert summary['class_counts_primary'] == {'A': 1, 'B': 1, 'C': 18, 'D': 11}
    write(art/'summary.json', summary)
    label_table = '\n'.join('| '+label+' | '+str(metrics[label])+' |' for label in (
        'PROCESS_SUPPORTED','PARTIALLY_SUPPORTED','ANSWER_WITHOUT_OBSERVED_SUPPORT','PROCESS_NOT_REQUIRED','INSUFFICIENT_EVIDENCE'))
    cases_table = '\n'.join('| `'+r['job_id']+'` | '+r['unit']+' | '+source[r['job_id']]['label']+' | '+str(source[r['job_id']]['selection_steps'])+' |' for r in primary)
    supp_table = '\n'.join('| `'+r['job_id']+'` | '+r['unit']+' | '+source[r['job_id']]['label']+' |' for r in supplementary)
    source_report = '''# FlowEvo 成功轨迹的过程完整性审计

## 结论与范围

现有主要 TRAIN/DEV 的31个独立成功 task/variation 中，2条具有完整公开过程支持，17条最终选择缺少足够的公开依据，另有2条部分支持、10条不需要复杂实验。对19条需要比较或阈值判断的轨迹，18条缺少充分的观测决策依据。这里的“缺少”描述日志中的证据，不能推出随机猜测，也不能推出所有成功都不可学习。

其中完整过程是温度测量与融冰。温度的“读数→阈值→盒子”关系仍保存在编译后的 L2 规则；L1 缺少运行中按读数重新选择目标的结构，并遗漏末次必要的 focus。因此证据更支持先核查成功数据的过程含量，并做针对性的表示修复；尚不足以把总体问题归结为编译器抹掉了多数完整科学方法。

父提交为 `5ae0dcdf80bf81c4f5acd34d24f75501ddda942b`。本阶段新增实验模型请求0次、新增API费用0、新JVM回放0、新TEST求解0，没有重报任务成功率。运行时代码、治理、检索、直接执行、引导和回退均未改动。这里的0调用指实验 provider 请求；两次助手审阅不被包装成两名人类专家审阅。

## 样本与独立审阅

共建立102条历史成功记录的关联库存：31条主集、8条补充版本/重复运行、63条仅作元数据描述的TEST记录。主集为 F 组 discovery-v2、selected-train-v1、dev-baseline-v1，31条恰为31个不同task/variation。8条补充中只有3个主集之外的新单元，另5条是主集单元的版本重复，不能增加主统计权重。旧主基线42条成功包括31条TRAIN/DEV和11条F组TEST，不与102条跨组/版本库存混用。

所有39条TRAIN/DEV成功记录都有公开轨迹、保存的编译请求及响应；37条有独立编译结果文件，2条仅恢复请求响应。历史环境成功由原记录三处相符字段确认，只用于纳入库存，不作为选择哪个对象的依据。公开反馈、look、inventory仍用于过程审阅，隐藏判分、正确答案与专家路径未进入绑定或变体设计。

先生成仅有原始公开目标、状态、动作、反馈和saved reason的源包，再逐条审阅；编译字段不进入源包。两份助手审阅均覆盖39条，38条标签一致。主审已有项目背景，第二审阅分支在源审阅时只读源包；这不是严格盲态的两人专家一致性实验。熔点110的唯一分歧从“选择无依据”裁为“部分支持”：有一次当前温度测量，但没有测到熔点，双方均认为选择没有充分依据。冻结后才连接编译文件，原标签、分歧和哈希均保留。

`INSUFFICIENT_EVIDENCE`指日志缺失到无法判定；当前完整日志没有观察到所需物理证据，通常属于`ANSWER_WITHOUT_OBSERVED_SUPPORT`，二者不混淆。角色和适用条件的语义审阅另由第二审阅完成，主审复核关键案例，未宣称其经过两份独立编译标注。

| 源标签 | 主集数量（分母31） |
| --- | ---: |
LABEL_TABLE

## 六项指标

以下是固定成功语料的描述性全量审计，非随机抽样推断；不给误导性的总体置信区间，也不计算新的任务成功率。

| 指标 | 结果与分母 | 解释 |
| --- | --- | --- |
| 有完整过程支持 | 2/31（6.5%）；复杂推断/实验任务内2/20（10.0%） | 10条简单类别任务和1条活物状态异常单列 |
| 缺关键决策依据 | 比较/阈值任务18/19（94.7%）；全主集18/31（58.1%） | 17条无充分依据＋熔点部分支持；不等于随机猜中 |
| 关键步骤保留 | 实验核心2/2；包括必要完成标记1/2 | 温度测量和放盒保留，末次focus缺失；融冰核心保留 |
| 参数角色与条件联合支持 | 6/31有支持，4/31有明确缺陷，21/31不确定 | 角色7真/3假/21未知；条件29真/1假/1未知；不是31条的失败率 |
| 观测—决策依赖保留 | 来源确有此关系的1条中，L1可执行分支0/1；raw/L2规则文本1/1 | 分母只有温度例，不能推广为整个编译器“全部丢失” |
| 可信完整迁移候选 | 1个保留方法的结构候选（融冰）；完整迁移已验证0个 | 12个静态条件检查未放行完整序列，未做真实迁移求解 |

条件“支持”仅指原applicability描述与来源事实相容，不表示足以覆盖所有未来世界状态；参数角色“支持”要求可辨别的来源对象/房间角色与确定对齐，别名或多重对齐保守记未知。温度盒子参量独立与观测决定盒子的关系是两个维度，前者支持不挽救后者。

## 逐类证据

### 温度：观察确实解释了选择

`discovery-v2.F.2beaa66b5bcd3db3dc64`，use-thermometer:151。目标明确高于0°C用蓝盒、低于0°C用橙盒。第9步测得−13°C；第10步reason使用小于0的判断，第14步放入橙盒，第15步查看确认，第17步focus物质完成。测量与动作之间有公开可核查关系。reason不是测量的替代品，测量来自环境反馈。

### 融冰：有可见的状态变化

`discovery-v2.F.6aebd9fb1322c1074fb6`，melt:4。第5步开冰箱、第6步有效focus冰、第7步拾取、第8步放炉上、第9步启动炉子；第9步公开look由ice变为water。第3步无效focus不是必要步骤，编译删除它不构成信息损失。补充版本的棉花糖任务也有热源、放置及第11步wait后液态反馈，但它不增加主集分子。

### 斜面：10条来源均未观察到充分的摩擦比较

在10条主集摩擦任务中，look给出名称/表面信息，connect的实际反馈是端子连接，focus承担选择而非摩擦测量。不能把存在这些接口动作当作已进行了科学比较。例如钛/锌 `selected-train-v1.F.003597b7b9c549df70c6` 第1/2步观察两面，第3/4步连接，第5步focus钛，没有滑动时间或比较反馈。匿名面 `discovery-v2.F.9cef108e88fa0d6aff89` 也没有可解释选择的测量。材料常识可能影响模型判断，但日志没有证明它可靠地区分了当题物理结果。

### 寿命：5条缺少公开寿命排序；知识先验不能被当作已测量

可见内容为物种名和生命阶段，没有寿命数值或可核查排序。有些reason使用刺猬较短、龟较长等先验，有些将focus误作查看。严格公开证据口径下标记无充分依据；不声称知识类问题一律必须现场测量，也不把“未记录依据”改写为“随便猜”。两条先最长后最短的源轨迹有双选择顺序，虽无验证排序，顺序本身仍可审查编译保真。

### 遗传：2条没有公开的杂交/后代证据

`discovery-v2.F.5338a5b7b1763d020e75`与`discovery-v2.F.ae8d0d5850873ad49924`只观察种子、容器并拾取/选择，没有种植、杂交或后代性状比较。最终颜色盒选择的科学依据未在来源中出现，因此缺失遗传推断不能归因于编译删除。

### 熔点：当前温度不是熔点

`discovery-v2.F.3fbe681bf784f2d76d21`，measure-melting-point-unknown-substance:110。第5步测得固体当前10°C；没有加热、熔化或相变平台。第6步reason从“等于10、既不大于也不小于”转成选择橙盒，不能建立目标要求的熔点分支。裁定部分支持，最终决策不支持；环境原成功字段保持原样。

### 简单类别与状态异常

10条找非生物/植物/动物的任务按类别搬运，不强求实验比较，标为PROCESS_NOT_REQUIRED。这不保证路径高效或状态持续有效：蜂可逃逸，源轨迹也多次检查和重新拾取。例如`dev-baseline-v1.F.cfcb5065ead3594fa047`第75步放蜂、第76步查看、第77步focus；另一些任务最终公开盒内容为空，须保留这个状态现象而不重写历史成功。其L2仍包含重取策略，不能概括为完全丢掉状态反馈。

活物 `discovery-v2.F.b305a2703799b76c3a98` 初始正确识别adult pea plant，但第6步已经dead，第7步实际搬运dead pea plant；这是部分支持的持续状态问题，不能归入复杂科学比较失败。它与任务只要求plant的另一个样本不同。

## 四类归因与研究判断

| 类别 | 主集数量 | 本次解释 |
| --- | ---: | --- |
| A 来源过程完整、关键方法保留 | 1 | 融冰，结构候选，未证明迁移 |
| B 来源过程完整、某层关键结构缺失 | 1 | 温度，L1分支/末focus缺失，L2阈值规则仍在 |
| C 成功但关键决策依据不足 | 18 | 17条无充分依据＋熔点部分支持；仍可能同时有可辨认的角色/步骤缺陷 |
| D 简单或部分状态案例 | 11 | 10条简单＋活物状态异常；不强行称为算法失败 |

当前证据首先质疑“环境成功即可作为完整可迁移方法来源”的充分性。它没有证明采用新的过程技能算法优于保留适用条件、分离角色、补足必要标记等简单修正。先以源过程证据做质量审查，保留L2已有规则，修复可定位的状态/角色与完成标记问题，再对融冰及温度做不收费的验证，具有更明确的依据。仍不建议据此宣称失败学习或新编译算法有效，也不自动启动付费验证。

## 主集逐条索引

步骤编号从1开始；详细measurement/comparison/selection索引、源文件字节/语义哈希、原服务器哈希及生命周期见[来源CSV](../results/success_trace_audit.csv)。完整公开轨迹可用复算脚本恢复，可读源包位于[源包目录](../artifacts/success_audit/source_packets)。

| 轨迹ID | 独立单元 | 源标签 | 最终选择相关步骤 |
| --- | --- | --- | --- |
CASES_TABLE

## 补充版本，独立于主统计

| 轨迹ID | 单元 | 源标签 |
| --- | --- | --- |
SUPP_TABLE

## 复核材料

[信息损失报告](COMPILATION_INFORMATION_LOSS_ZH.md)、[矩阵CSV](../results/skill_information_loss.csv)、[复算说明](SUCCESS_AUDIT_REPRODUCE.md)、[审阅冻结](../artifacts/success_audit/source_review_freeze.json)、[分歧记录](../artifacts/success_audit/review_disagreements.json)、[机器统计](../artifacts/success_audit/summary.json)和[执行核验](../artifacts/success_audit/verification.json)共同构成证据链。历史TEST只保留索引及既有元数据，本次没有增加TEST过程标签或成绩表。
'''.replace('LABEL_TABLE', label_table).replace('CASES_TABLE', cases_table).replace('SUPP_TABLE', supp_table)
    unsupported_table = '\n'.join('| `'+r['job_id']+'` | '+str(review[r['job_id']]['l2_unobserved_effect_rule_indices'])+' | '+ '；'.join(review[r['job_id']]['unsupported_additions_zh'])+' |' for r in primary if review[r['job_id']]['l2_claims_unobserved_experimental_effect'])
    loss_report = '''# 成功技能编译的信息损失与迁移结构审计

## 可以归因于什么

不能把源轨迹本来没有的比较实验归为编译损失。31个主要TRAIN/DEV成功单元中，18个比较/阈值任务缺少充分来源决策证据；这部分科学方法的编译保真度为NOT_IDENTIFIABLE。另一方面，来源动作的对象角色、状态、顺序与完成标记依然可以检查，不因缺少科学方法而跳过。

实际发现分为四层：公开状态输入未截断；raw输出出现部分角色压缩和无依据效果描述；历史L1序列化丢掉applicability；L1固定绑定表达不了新观测驱动的分支，而L2仍保留温度判断规则和一些状态恢复策略。不存在“所有信息全被编译器丢掉”的证据。

## 完整关联及缺失记录

39份TRAIN/DEV编译请求的user JSON均与完整public_episode投影逐项相等：目标、初始公开状态和全部步骤的动作/反馈/look/inventory都在，39/39没有这些字段的裁剪。保存的reason未传入（其中一条直接技能来源本无模型reason），属于输入接口差异；不能将reason里的未经验证主张提升为环境证据。

39份原始响应均可恢复，37份还有单独编译文件：raw_parsed与响应相同，37/37的L2规则与raw的前5条逐字相同。缺编译文件的是`discovery-v1.F.965d4f1df81ea937ed3b`和`discovery-v1.F.e1913f9868b6d9fe9f61`，仅恢复输出，不补造历史通过/拒绝或准入结论。

缓存来源验证15/39通过，主集13/31通过；它只验证实例动作是来源有序子序列，不保证科学正确、完整完成目标或未来房间连通。37份有文件的历史通过/拒绝与缓存重算一致。当前34份A2旧审阅记录（主集31＋重复3）和本次增加的discovery-v1五条不能作为39个独立task/variation。没有重新生成或准入技能。

库存与矩阵保留run/arm/split、episode和task/variation、恢复文件SHA256、原服务器SHA256、规范JSON哈希、请求/响应引用及哈希、编译文件状态、历史准入事件与按split分开的检索/实际使用。生命周期来自已保存银行事件和episode source字段；同一事件可能被多个bank快照重复保存，不能把事件列表长度当作独立准入次数。retrieved也不等于direct_skill或skill_guided实际动作。63条TEST只连接历史元数据，不看作新设计样本。

## 信息损失矩阵的读法

[skill_information_loss.csv](../results/skill_information_loss.csv)共102行，每条成功记录一行，与来源CSV按job_id一对一连接。39行含完整审计，63行标NOT_AUDITED_TEST。空值表示未知、不适用或未审阅，不能当作False。每行并列原始依据、输入、raw、L1、L2和生命周期，`information_losses_zh`、`retained_information_zh`、`unsupported_additions_zh`与`attribution_scope_zh`解释层次。

| 维度 | 主集结果 | 不可作出的推论 |
| --- | --- | --- |
| 来源科学过程 | 完整2、部分2、选择证据不足17、简单10 | 环境成功不等于完整方法；缺证据不等于随机 |
| 来源完整案例的实验核心 | 2/2保留测量/热操作 | 不意味着整个目标过程完整 |
| 必要完成标记覆盖 | 1/2；温度遗漏源17 | 不能禁止focus；应区分测量、选择和任务完成 |
| 来源对象角色 | 7/31支持、3/31明确损失、21/31未知 | 多重对齐或别名不等于确定错误，也不能冒充语义正确 |
| 原适用条件与来源相容 | 29/31支持、1/31不支持、1/31未知 | 相容不等于完备、可自动求值或适合任意任务 |
| 角色及条件联合 | 6/31支持、4/31有缺陷、21/31未知 | 字段存在不是方法保真 |
| 历史L1保留applicability | 主集0/13，全部有效模板0/15 | 这是可定位的序列化缺失 |
| A2缓存模板/库往返保留applicability | 主集13/13，全部15/15 | 仅验证已完成工程修复；不回填历史产物、不证明条件充分 |
| raw规则到历史L2 | 主集31/31；全部有文件37/37 | 文本保留不证明其中科学陈述有来源支持 |
| 来源观测—决策关系 | 分母1；L1可执行分支0/1，L2文本1/1 | 不能合并成FlowEvo整体0/1 |

参数角色严格检查来源参照物及对象/房间分离；固定block保留字面量且新状态提供brick时，不自动把brick替换为block。温度独立的box参数仍需要新的测量驱动绑定；A2标签把它称为transfer_destination而未独立解决goal_choice语义，不能靠字段名声称已经恢复决策。

## 关键证据链

### 温度：L2保留关系，L1缺动态分支和完成标记

`discovery-v2.F.2beaa66b5bcd3db3dc64`源第9步−13°C、第10/14步依据0°C阈值选橙盒、第17步focus物质。raw动作对应源`[1,3,5,6,7,8,9,10,11,12,13,14]`，测量未被删，放盒也在；缺第17步。raw第3条规则明确高于0用蓝盒、低于0用橙盒，并原样进入L2。applicability也有条件文本。

实际`ScienceExecutor._execute_direct`在执行前一次instantiate所有动作，执行中的新读数不触发重新绑定box。故缺陷是L1的可执行依赖以及末端动作覆盖；不是没有保存阈值知识。L2引导及失败回退的模型可能使用这条规则，但本次不调用模型，既不声称它一定修复，也不声称它一定失败。

### 融冰：保留方法，尚无泛化证据

`discovery-v2.F.6aebd9fb1322c1074fb6` raw对应源`[1,2,5,6,7,8,9]`，开容器、有效focus、拾取、放炉、启动均保留；规则要求检查状态变化。room/container/substance/device分离，来源唯一对齐。这是1个值得继续免费核验的结构候选。初始状态完整绑定仍被既有保守条件检查拒绝，不能报告它已经完成新任务。

补充棉花糖`discovery-v1.F.279ad8d80a9088c7546b`虽保留加热/放置/wait，但L1删除中间到kitchen的导航，L2仍描述正确导航关系。该差异单列，不增加主集分子。

### 钛/锌斜面：来源无比较，不是丢失已有比较

`selected-train-v1.F.003597b7b9c549df70c6`三步模板仅对应源`[1,3,5]`，另一面的look和连接被删，是操作覆盖的压缩。来源两面的连接也只有端子反馈，无摩擦值或比较结果；因此不能声称编译器删除了一套完整摩擦算法。它还固定字面block，不能在brick公开状态下悄悄替换。L2把connect/focus解释成摩擦测量，是超出来源证据的效果描述。

### 房间、容器、状态与双目标

- `selected-train-v1.F.1421639dc7e19fcaab35`唯一结构对齐需要room同时表示hallway和workshop，单绑定无法复现；历史来源验证拒绝。
- `discovery-v2.F.def63cb9dcbcef266a65`的destination既用于中转kitchen，又用于最终yellow box，混合房间与容器；L2仍区分导航和最终容器。
- `discovery-v2.F.b305a2703799b76c3a98`源第6步dead、第7步move dead完整进入输入，raw却以adult例值实例化。对象可能是同一植株，但状态变化不能抹平，不能凭别名统一成健康活物。
- 两条先最长再最短`31452f59c48bc5d93974`、`8a0e00d29345445b21a5`的raw L1仅一次focus；L2仍明确双选择顺序。其来源没有可验证寿命排序，故排序推断的保真不可识别，但动作顺序压缩可确定。
- 蜂搬运中会逃逸，`dev-baseline-v1.F.cfcb5065ead3594fa047`的L1有序子序列并不覆盖全过程导航及持有状态，L2第5条保留丢失后重取。不能一概称反馈/恢复全部消失。

## 无来源支持的效果新增，区别于信息丢失

严格口径为规则声称某操作产生了本轨迹未观察到的实验效果，而非仅提及任务目标。主集9/31条符合：8条摩擦、1条熔点；其余类似“比较完成后再focus”的目标性描述不自动计入。这些描述已经出现在raw，L2忠实保存它们；问题在归纳依据，不能归为L2序列化损失。也没有新实验能量化它们的实际有害程度。

| 轨迹ID | L2规则索引（1起） | 依据 |
| --- | --- | --- |
UNSUPPORTED_TABLE

## 12项无需模型的结构检查

检查计划在读取执行结果前保存为[transfer_plan.json](../artifacts/success_audit/transfer_plan.json)，结果为[transfer_checks.json](../artifacts/success_audit/transfer_checks.json)。只枚举公开可见对象或明确标注的虚拟反馈，无新技能、无JVM动作、无隐藏分数。

| 变化 | 静态项数 | 可得结论 |
| --- | ---: | --- |
| 来源titanium/zinc，比较未知 | 2 | 两面都检查；模板不包含获得两面物理结果并比较的分支 |
| steel/rubber，实验对象brick | 2 | plane可取公开名称，固定block不能据此合法替换为brick |
| least改为most（虚拟目标） | 2 | 同一绑定不让模板自动翻转选择；未知比较仍为INSUFFICIENT_EVIDENCE |
| DEV斜面尚不可见 | 1 | 不补造对象，条件不放行 |
| 同一DEV第5步后两面可见 | 2 | 重新判定；对象可见仍不足以放行完整模板或决定哪面 |
| 温度−13/+13虚拟反馈 | 2 | 给定相同example bindings，L1动作完全相同；L2阈值文本仍在 |
| 融冰来源初始状态 | 1 | 检查结构候选；保守前提不放行完整序列 |

12/12未被现有条件检查放行完整模板，不等于执行失败率，也不证明不存在合适的后续状态。当前checkpoint有效动作集合不是所有未来步骤的集合，因此结果里的membership缺失只描述当时状态。负/正温度是表示敏感性测试，不声称+13曾在该环境出现，也不推断新模型一定选择相同绑定。没有用哪个focus得100分倒推plane。

## 研究边界与下一步

不需要凭此次审计直接提出新算法。优先保持现有来源验证和动作安全检查，保留已恢复的applicability，再针对可定位的角色合并、必要focus遗漏和晚到观测绑定做小范围修正与免费验证。成功样本的准入依据若只看终局成功，仍无法保证存在值得提炼的科学方法；但本次没有改变准入政策，也没有用过程标签重新筛选历史成绩。

分支仅增加离线审计脚本、冻结标注、脱敏数据矩阵和报告。来源验证通过只是来源子序列证据；15个通过不等于15个完整技能，1个结构候选不等于已经具备完整迁移能力。保留简单基线、失败和未知，有收益与否留待合适的免费机制检查或用户另行授权实验。

[来源报告](SUCCESS_TRACE_INTEGRITY_ZH.md)给出31个独立样本和8个补充版本索引；[复算说明](SUCCESS_AUDIT_REPRODUCE.md)说明固定依赖、原始字节核验和零API隔离；[执行回执](../artifacts/success_audit/verification.json)记录账本、运行时代码及测试核验。
'''.replace('UNSUPPORTED_TABLE', unsupported_table)
    (out/'reports/SUCCESS_TRACE_INTEGRITY_ZH.md').write_text(source_report, encoding='utf-8')
    (out/'reports/COMPILATION_INFORMATION_LOSS_ZH.md').write_text(loss_report, encoding='utf-8')
    (out/'SUCCESS_AUDIT_README.md').write_text('''# 成功轨迹过程完整性与技能信息保真审计

基于 `5ae0dcd`，新增实验API调用0次、费用0，不改运行时代码，不重新报告任务成功率。

- [成功轨迹中文报告](reports/SUCCESS_TRACE_INTEGRITY_ZH.md)
- [编译信息损失中文报告](reports/COMPILATION_INFORMATION_LOSS_ZH.md)
- [来源逐条CSV](results/success_trace_audit.csv)
- [技能信息损失矩阵CSV](results/skill_information_loss.csv)
- [复算说明](reports/SUCCESS_AUDIT_REPRODUCE.md)
- [执行核验](artifacts/success_audit/verification.json)

主集31个独立TRAIN/DEV单元：完整过程2、部分支持2、选择证据不足17、简单10。比较/阈值任务18/19缺少充分观测决策依据；这不是随机猜测的证明。温度观测—阈值关系在L2保留，L1缺动态分支和末次focus；融冰保留关键过程，是1个结构候选，完整迁移仍未证明。

39条源审阅在连接编译文件前冻结。8条补充版本单列，63条TEST仅历史元数据。56项测试通过，12项静态检查无新环境求解。两份助手审阅不是两位人类专家，未知不计为失败。
''', encoding='utf-8')
    print(encoded({'matrix_records': len(rows), 'primary_units': len(primary), 'summary': summary}))

if __name__ == '__main__': main()
