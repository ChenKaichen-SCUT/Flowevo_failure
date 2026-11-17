"""Free JVM identity checks and accepted preparation fragments, never new solves."""
import argparse,json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from engineering_common import read,write,digest,records

def execute(payload):
    root,case=payload
    from flowevo_sw.adapter import ScienceWorldAdapter
    from flowevo_sw.action_gateway import ActionGateway
    episode=read(Path(root)/'input-snapshot/episodes'/(case['job_id']+'.json'))
    env=ScienceWorldAdapter();observed=[]
    try:
        env.reset(episode['spec']['task_name'],episode['spec']['variation_id'])
        assert digest(env.view)==digest(episode['initial'])
        for step in episode['steps'][:case['checkpoint']]:
            env.execute(step['executed_action']);assert digest(env.view)==step['observation_hash']
        assert digest(env.view)==case['public_hash']
        if case['kind']=='identity':
            original=episode['steps'][case['checkpoint']];gateway=ActionGateway(env,arm='F')
            gateway.step(original['executed_action'],source=original['source'],raw=original.get('raw_model_response'),request_id=original.get('request_id'))
            actual=gateway.steps[0];assert actual['executed_action']==original['executed_action']
            assert actual['observation_hash']==original['observation_hash']
            observed.append({'action':actual['executed_action'],'public_hash':actual['observation_hash'],'interface_audit':actual['interface_audit']})
        else:
            assert case['preparation_only'] and case['source_validation']
            for action in case['actions']:
                assert not action.startswith('focus on '),'No goal-choice action in these preparation probes'
                assert action in env.view['valid_actions'],'Original direct-execution safety gate'
                env.execute(action);observed.append({'action':action,'feedback':env.view['observation'],'public_hash':digest(env.view)})
        return {'case':case,'prefix_hashes_verified':True,'observations':observed,'new_api_calls':0,
            'classification':'IDENTITY_VERIFIED' if case['kind']=='identity' else 'PREPARATION_ACTIONS_EXECUTABLE_ONLY',
            'full_task_transfer_verified':False,'task_success_rate_computed':False}
    finally:env.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='..');parser.add_argument('--workers',type=int,default=4);args=parser.parse_args()
    root=Path(args.root).resolve();out=root/'output';eps=records(root/'input-snapshot');cases=[]
    fixed=['02e77cda31db3b964346','0ef2ea6f576b10fb9a37','20e65c56c84af8ab157f','81f896325b22612a849e',
           'd129caa70cba348ea3e4','1b4703786cd7f2ff0592','06eebbde9128242aba13','5de4ccea5ffbd8f8b877']
    checkpoints=[('discovery-v2.F.'+suffix,len(eps['discovery-v2.F.'+suffix]['steps'])-1) for suffix in fixed]
    checkpoints.extend([('selected-train-v1.F.003597b7b9c549df70c6',4),('discovery-v2.F.7ac4185e5f00f742931e',0),('dev-baseline-v1.F.cfcb5065ead3594fa047',3)])
    therm=eps['discovery-v2.F.06eebbde9128242aba13']
    checkpoints.append((therm['job_id'],next(i for i,s in enumerate(therm['steps']) if s['executed_action']=='focus on thermometer')))
    for jid,n in checkpoints:
        episode=eps[jid];assert episode['spec']['split'] in ('train','dev')
        cases.append({'kind':'identity','job_id':jid,'checkpoint':n,'public_hash':digest(episode['steps'][n]['before']),
            'selection':'Fixed known errors plus mandatory-focus and normal-wording controls; action unchanged'})
    deduplicated={}
    for candidate in read(out/'artifacts/engineering/accepted_binding_prefixes.json'):
        assert candidate['preparation_only'],'Whole-skill validation is outside this preparation check'
        key=(candidate['job_id'],candidate['checkpoint'],tuple(candidate['actions']))
        if key not in deduplicated:deduplicated[key]=dict(candidate,kind='preparation',equivalent_variants=[])
        deduplicated[key]['equivalent_variants'].append(candidate['variant'])
    cases.extend(deduplicated.values())
    plan={'cases':cases,'maximum_workers':args.workers,'new_API_calls':0,'no_TEST':True,'no_model_continuations':True}
    path=out/'artifacts/engineering/jvm_plan.json'
    if path.exists():assert read(path)==plan
    write(path,plan)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:results=list(pool.map(execute,[(str(root),case) for case in cases]))
    write(out/'artifacts/engineering/jvm_receipts.json',results)
    print(json.dumps({'identity_cases':len(checkpoints),'unique_preparation_branches':len(deduplicated),'new_api_calls':0,'full_task_transfer_verified':False}))
if __name__=='__main__':main()
