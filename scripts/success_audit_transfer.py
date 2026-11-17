"""Structural perturbations only: no solver, new skill, JVM action or score."""
import argparse,copy,inspect,json,os
from pathlib import Path
from success_audit_prepare import read,write,sha,canonical

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    inp=Path(a.input).resolve();out=Path(a.output).resolve();art=out/'artifacts/success_audit'
    assert os.environ.get('FLOWEVO_OFFLINE_ONLY')=='1'
    from flowevo_sw.skill_contracts import ScienceSkillTemplate
    from flowevo_sw.conditional_binding import conditional_bind,public_references
    from flowevo_sw.flowevo_adapter import ScienceExecutor
    chain={c['job_id']:c for c in read(art/'compilation_chain.json')};cases=[]
    plane_id='selected-train-v1.F.003597b7b9c549df70c6';therm_id='discovery-v2.F.2beaa66b5bcd3db3dc64';melt_id='discovery-v2.F.6aebd9fb1322c1074fb6'
    plane=ScienceSkillTemplate.from_dict(chain[plane_id]['current_cached_template'])
    def state(jid,checkpoint):
        packet=read(art/'source_packets'/(jid+'.json'));assert packet['identity']['split'] in ('train','dev')
        return copy.deepcopy(packet['initial'] if checkpoint==0 else packet['steps'][checkpoint-1]['after']),packet['identity']['split']
    for kind,jid,checkpoint,flip in [
      ('SOURCE_MATERIALS_UNKNOWN_COMPARISON',plane_id,0,False),
      ('STEEL_RUBBER_WITH_BRICK','selected-train-v1.F.098816d79aa10bdc5eec',2,False),
      ('SYNTHETIC_LEAST_TO_MOST',plane_id,0,True),
      ('BEFORE_VISIBILITY','dev-baseline-v1.F.3ea7c55db1ecffae3c8a',0,False),
      ('AFTER_VISIBILITY','dev-baseline-v1.F.3ea7c55db1ecffae3c8a',5,False)]:
        view,split=state(jid,checkpoint);origin=sha(canonical(view))
        if flip:view['goal']=view['goal'].replace('least friction','most friction')
        planes=sorted(x for x in public_references(view) if x.startswith('inclined plane with a '))
        for candidate in planes or [None]:
            mapping={'plane':candidate} if candidate else {}
            cases.append({'kind':kind,'source_template_job':plane_id,'state_job':jid,'split':split,'checkpoint':checkpoint,
              'synthetic':flip,'source_public_sha256':origin,'view':view,'bindings':mapping})
    # Hypothetical thermometer feedback tests representation sensitivity only.
    # The second value is not asserted to have occurred in ScienceWorld.
    for reading in (-13,13):
        view,split=state(therm_id,9);origin=sha(canonical(view))
        view['observation']='the thermometer measures a temperature of '+str(reading)+' degrees celsius'
        cases.append({'kind':'SYNTHETIC_MEASUREMENT_SIGN_CHANGE','source_template_job':therm_id,'state_job':therm_id,'split':split,'checkpoint':9,
          'synthetic':True,'synthetic_reading':reading,'source_public_sha256':origin,'view':view,
          'bindings':chain[therm_id]['raw']['example_bindings']})
    # The method-preserving melt candidate is assessed without claiming parser coverage.
    view,split=state(melt_id,0)
    cases.append({'kind':'MELT_METHOD_CANDIDATE','source_template_job':melt_id,'state_job':melt_id,'split':split,'checkpoint':0,
      'synthetic':False,'source_public_sha256':sha(canonical(view)),'view':view,'bindings':chain[melt_id]['raw']['example_bindings']})
    plan={'selection':'Fixed source/steel-rubber/late-visible TRAIN/DEV states; every visible plane enumerated; two explicitly synthetic temperature readings',
      'cases':cases,'new_model_calls':0,'new_skills_generated':0,'target_score_used':False}
    path=art/'transfer_plan.json'
    if path.exists():assert read(path)==plan,'Frozen structural plan changed'
    write(path,plan)
    results=[]
    for case in cases:
        template=ScienceSkillTemplate.from_dict(chain[case['source_template_job']]['current_cached_template'])
        view=case['view'];binding=case['bindings']
        try:actions=template.instantiate(binding)
        except KeyError:actions=None
        verdict=conditional_bind(template,view,binding)
        current_invalid=[x for x in actions or [] if x not in view['valid_actions']]
        results.append({k:v for k,v in case.items() if k!='view'}|{'instantiated_actions':actions,'condition_verdict':verdict,
          'actions_not_currently_valid_at_this_checkpoint':current_invalid,
          'membership_check_scope':'Current-checkpoint membership only, not execution of a future multi-step plan; original stepwise guard unchanged',
          'physical_comparison_evidence':'INSUFFICIENT_EVIDENCE' if case['source_template_job']==plane_id else 'SYNTHETIC_PERTURBATION_NOT_ENVIRONMENT_MEASUREMENT' if case['synthetic'] else 'SOURCE_STATE_CHANGE_ONLY',
          'full_transfer_demonstrated':False})
    temperature=[r for r in results if r['kind']=='SYNTHETIC_MEASUREMENT_SIGN_CHANGE']
    assert temperature[0]['instantiated_actions']==temperature[1]['instantiated_actions']
    assert all(not r['condition_verdict']['accepted'] for r in results)
    receipt={'cases':results,'new_model_calls':0,'new_JVM_actions':0,'target_score_used':False,'new_skills_generated':0,
      'L1_same_binding_actions_invariant_to_new_temperature':True,
      'L2_temperature_rule_retained_verbatim':chain[therm_id]['raw']['rules'][2],
      'execution_semantics_ref':'src/flowevo_sw/flowevo_adapter.py#ScienceExecutor._execute_direct',
      'execution_semantics_sha256':sha(inspect.getsource(ScienceExecutor._execute_direct).encode()),
      'limitation':'Full L1 action sequence is instantiated once before execution. A late new measurement does not rebind parameters. L2 model-guided use is a separate untested route. No physical response is inferred from a synthetic state.'}
    write(art/'transfer_checks.json',receipt)
    print(json.dumps({'static_cases':len(results),'new_model_calls':0,'full_transfers_demonstrated':0,'temperature_L1_actions_invariant':True}))
if __name__=='__main__':main()
