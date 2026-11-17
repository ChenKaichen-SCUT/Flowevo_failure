import argparse,json
from pathlib import Path
from flowevo_sw.deepseek_client import DeepSeekClient
from flowevo_sw.contrastive_learner import RULE_PROMPT
from flowevo_sw.invariant_schema import validate_rule
from flowevo_sw.checkpointing import atomic_json,read_json,digest

def strip_private(probe,success_only=False):
    branches=probe['branches'][1:] if success_only else probe['branches']
    if success_only and probe.get('independent_public_adjudication',{}).get('recovery_suffix'):
        branches=[{'name':'observed_recovery_suffix','steps':probe['independent_public_adjudication']['recovery_suffix']}]
    from flowevo_sw.shared_state import public_facts,action_facts
    compact=[]
    for b in branches:
        steps=[]
        for s in b['steps']:
            before={k:s['before'][k] for k in ('goal','look','inventory')}
            # F-S receives no prior failure observation, verdict, or contrast label.
            if not success_only:before['observation']=s['before']['observation']
            before['public_facts']=public_facts(s['before']);before['action_facts']=action_facts(s['before'],s['action'])
            steps.append({'action':s['action'],'before':before,'feedback':s['after']['observation'],'after':{k:s['after'][k] for k in ('look','inventory')},'syntactically_listed':s['action'] in s['before']['valid_actions']})
        compact.append({'name':b['name'],'steps':steps})
    return {'probe_id':probe['probe_id'],'branches':compact}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--probe-index',required=True);p.add_argument('--run-id',default='rules-v1');a=p.parse_args();root=Path(a.root).resolve();probes=read_json(a.probe_index);groups={}
    for r in probes:groups.setdefault(r['mechanism_id'],[]).append(r)
    versions=[]
    for mid,records in sorted(groups.items()):
        for arm in ('F-I','F-S'):
            path=root/'output/artifacts/rule_versions'/(a.run_id+'.'+mid+'.'+arm+'.json')
            if path.exists():versions.append(read_json(path));continue
            usable=records
            if arm=='F-S':usable=[r for r in records if r.get('independent_public_adjudication',{}).get('verified_precondition_repair')]
            if not usable:
                result={'arm':arm,'mechanism_id':mid,'rule':None,'reason':'NO_PUBLICLY_SUPPORTED_RECOVERY_SUFFIX'}
            else:
                client=DeepSeekClient(a.run_id+'.'+mid+'.'+arm,meta={'stage':'constraint_generation','arm':arm,'split':'train'})
                prompt=RULE_PROMPT if arm=='F-I' else RULE_PROMPT.replace('real local contrastive executions','publicly supported recovery suffixes only')
                prompt+=' Additional shared public fields: action_verb and action_target are parsed from action syntax; target_door_state and target_container_state are open/closed only when explicitly described in the CURRENT look, otherwise unknown. All arms also see these literal current door/container maps. These fields contain no action recommendations.'
                obj,raw,rid,usage=client.json(prompt,{'evidence':[strip_private(r,arm=='F-S') for r in usable]},stage='rule_generate',learning=True)
                rule=obj.get('rule');error=None
                if rule is not None:
                    try:
                        validate_rule(rule);rule['rule_id']=a.run_id+'.'+mid+'.'+arm;rule['source_evidence_ids']=[r['probe_id'] for r in usable];rule['validation_status']='CANDIDATE'
                    except ValueError as exc:error=str(exc);rule=None
                result={'arm':arm,'mechanism_id':mid,'rule':rule,'raw':raw,'request_id':rid,'usage':usage,'schema_error':error,'reason':obj.get('reason'),'generation_index':1,'functional_revisions':0}
            atomic_json(path,result);versions.append(result)
    atomic_json(root/'output/artifacts/candidate_rules.json',versions);print(json.dumps({'candidates':sum(bool(v['rule']) for v in versions),'total':len(versions)}))
if __name__=='__main__':main()
