"""All eligible baseline TRAIN/DEV saved templates/states; no answer selection."""
import argparse,collections,itertools,json,re
from pathlib import Path
from flowevo_sw.skill_contracts import ScienceSkillTemplate
from flowevo_sw.flowevo_adapter import ScienceCompiler
from flowevo_sw.batch_runner import restore_trace,public_episode
from flowevo_sw.conditional_binding import roles,source_valid,repair_source_parameters,lift_literal_experiment_object,preparation_prefix,conditional_bind,public_references
from engineering_common import read,write,csv_write,records,digest

RUNS={'discovery-v2','selected-train-v1','dev-baseline-v1','batch-sensitivity-1-v1','batch-sensitivity-8-v1'}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='..');args=parser.parse_args()
    root=Path(args.root).resolve();inp=root/'input-snapshot';out=root/'output';eps=records(inp)
    selected={jid:d for jid,d in eps.items() if d['run_id'] in RUNS and d['arm']=='F' and d['spec']['split'] in ('train','dev')}
    structure=[];candidate_files={};candidates=[];plan=[];binding_rows=[]
    for jid,d in selected.items():
        path=inp/'compilations'/(jid+'.json')
        if not path.exists():continue
        compilation=read(path)
        if not compilation:continue
        generated=compilation.get('raw_parsed') or {}
        if not generated.get('action_template'):continue
        source_actions=[x['executed_action'] for x in d['steps']]
        compiler=ScienceCompiler(None,public_episode(d));compiler.generated=generated
        cached_result=compiler.compile(restore_trace(d));template=cached_result.template
        assert bool(template)==bool(compilation.get('template')),'Cached source-validation regression '+jid
        diagnostic={'status':'ALREADY_SOURCE_VALID'}
        if template is None:
            template,diagnostic=repair_source_parameters(generated,source_actions,d['spec']['task_name'],jid,d['initial']['goal'])
        if template:
            template.applicability=generated.get('applicability','');template.source_contract.update(source_goal=d['initial']['goal'])
            template.parameter_roles=roles(template,d['initial']['goal'])
            assert source_valid(template,source_actions)
            # Round-trip through the real library must retain every new metadata field.
            from flowevo_sw.credit_accounting import ScienceSkillLibrary
            library=ScienceSkillLibrary();assert library.add_template(template)
            restored=ScienceSkillLibrary.from_dict(library.to_dict()).retrieve(template.task_type)['template']
            assert restored.to_dict()==template.to_dict()
            candidate_files[jid]=template.to_dict()
        structure.append({'job_id':jid,'task':d['spec']['task_name'],'original_source_valid':bool(compilation.get('template')),
            'repair_status':diagnostic['status'],'repaired_source_valid':bool(template),'raw_applicability':generated.get('applicability',''),
            'condition_preserved':template.applicability==generated.get('applicability','') if template else 'NO_VALID_TEMPLATE',
            'parameter_roles':json.dumps(template.parameter_roles if template else {},sort_keys=True),
            'repair_details':json.dumps(diagnostic,sort_keys=True),'transfer_verified':False})
    # A fixed input-only plan: initial state and first visible-plane state. No
    # scores, outcomes, action suffixes or TEST states participate in selection.
    for jid,d in selected.items():
        existing=d['retrieved'].get('template')
        if not existing:continue
        source=eps[existing['source_trace_id']];compiled=read(inp/'compilations'/(existing['source_trace_id']+'.json'))
        original=ScienceSkillTemplate.from_dict(existing);original.applicability=compiled['raw_parsed'].get('applicability','')
        original.source_contract={'source_goal':source['initial']['goal']};original.parameter_roles=roles(original,source['initial']['goal'])
        source_actions=[s['executed_action'] for s in source['steps']]
        variants={'retained_conditions':original};lifted=lift_literal_experiment_object(original,source_actions)
        if lifted:variants['literal_parameter_lift']=lifted
        for variant,template in list(variants.items()):
            fragment=preparation_prefix(template,source_actions)
            if fragment:variants[variant+'_preparation']=fragment
        checkpoints={0:d['initial']}
        if 'plane' in original.parameters:
            visible=next((s for s in d['steps'] if any(v.startswith('look at inclined plane with a ') for v in s['before']['valid_actions'])),None)
            if visible:checkpoints[visible['step']-1]=visible['before']
        for n,view in checkpoints.items():
            for variant,template in variants.items():
                proposed=[]
                if 'plane' in template.parameters:
                    planes=sorted(x for x in public_references(view) if x.startswith('inclined plane with a '))
                    for plane in planes:
                        if 'experiment_object' not in template.parameters:proposed.append({'plane':plane});continue
                        objects=sorted({m.group(1) for a in view['valid_actions'] if (m:=re.fullmatch(r'connect (.+) to '+re.escape(plane),a))})
                        proposed.extend({'plane':plane,'experiment_object':obj} for obj in objects)
                else:
                    saved=(d.get('binding') or {}).get('parsed',{}).get('bindings',{})
                    if saved:proposed.append(saved)
                if not proposed:proposed=[{}]
                for mapping in proposed:
                    item={'job_id':jid,'split':d['spec']['split'],'checkpoint':n,'variant':variant,
                          'template_id':template.template_id,'bindings':mapping,'public_hash':digest(view),
                          'preparation_only':template.source_contract.get('preparation_only',False)}
                    plan.append(item);candidates.append((item,template,view))
    frozen={'selection':'Every baseline TRAIN/DEV retrieved-template episode; initial and first visible-plane checkpoint; enumerate all public plane/connection candidates, no scoring selection','cases':plan}
    plan_path=out/'artifacts/engineering/binding_plan_v2.json'
    if plan_path.exists():assert read(plan_path)==frozen
    write(plan_path,frozen)
    accepted=[]
    for item,template,view in candidates:
        verdict=conditional_bind(template,view,item['bindings'])
        if verdict['accepted']:
            accepted.append(dict(item,actions=template.instantiate(item['bindings']),source_validation=source_valid(template,[s['executed_action'] for s in eps[template.source_trace_id]['steps']])))
        binding_rows.append({**{k:v for k,v in item.items() if k!='bindings'},'bindings':json.dumps(item['bindings'],sort_keys=True),
            'accepted':verdict['accepted'],'status':verdict['status'],'issues':';'.join(verdict['issues']),
            'condition_checks':json.dumps(verdict['conditions'],sort_keys=True),'raw_applicability':verdict['raw_applicability'],
            'whole_skill_transfer_verified':False})
    csv_write(out/'results/engineering/skill_representation_audit.csv',structure)
    csv_write(out/'results/engineering/conditional_binding.csv',binding_rows)
    write(out/'artifacts/engineering/repaired_source_candidates.json',candidate_files)
    write(out/'artifacts/engineering/accepted_binding_prefixes.json',accepted)
    from flowevo_sw.credit_accounting import ScienceSkillLibrary
    original_m0=read(inp/'M0.json');enriched=ScienceSkillLibrary.from_dict(original_m0)
    for template in enriched._templates.values():
        source=eps[template.source_trace_id];compilation=read(inp/'compilations'/(template.source_trace_id+'.json'))
        template.applicability=compilation['raw_parsed'].get('applicability','')
        template.source_contract={'source_goal':source['initial']['goal'],'metadata_restored_from_saved_compilation':True}
        template.parameter_roles=roles(template,source['initial']['goal'])
    restored=enriched.to_dict()
    for key,value in original_m0.items():
        if key=='templates':
            for tid,old in value.items():assert all(restored[key][tid][field]==v for field,v in old.items())
        else:assert restored[key]==value
    write(out/'artifacts/engineering/M0_with_conditions.json',restored)
    summary={'eligible_train_dev_episodes':len(selected),'compiled_candidates':len(structure),
        'source_repair_status':dict(collections.Counter(x['repair_status'] for x in structure)),
        'binding_cases':len(binding_rows),'binding_source_episodes':len({r['job_id'] for r in binding_rows}),
        'cached_compiler_source_checks':len(structure),'M0_templates_metadata_restored':len(enriched._templates),
        'binding_verdicts':dict(collections.Counter(r['status'] for r in binding_rows)),
        'new_model_calls':0,'TEST_states_used':0,'repaired_candidates_admitted_to_runtime':0,
        'limitations':'Bounded natural-language verifier; unsupported clauses stay UNKNOWN. No material/property oracle and no goal-choice selection. Source validity is not transfer.'}
    write(out/'artifacts/engineering/binding_summary.json',summary);print(json.dumps(summary))
if __name__=='__main__':main()
