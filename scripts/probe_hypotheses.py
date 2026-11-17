"""Preplanned, finite TRAIN branches; never consult score when planning/retrying."""
import argparse,json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from flowevo_sw.adapter import ScienceWorldAdapter
from flowevo_sw.deepseek_client import DeepSeekClient
from flowevo_sw.checkpointing import atomic_json,read_json,digest

PLAN='''Design ONE bounded local public-state contrast for this proposed state mechanism. You see the same public checkpoint that preceded the observed action. Return {"alternative_actions":["at most 8 exact commands"],"expected_public_effect":"specific publicly observable effect","why_this_is_a_state_test":"...","original_action_after_preparation":true|false,"positive_feedback_substrings":["short concrete public phrases expected after repair"],"negative_feedback_substrings":["public phrases that would contradict the claim"]}. Prefer prepare-the-state then execute the original action, if that tests the hypothesis. No unseen properties, hidden goals, score assumptions, or expert solutions. Return an empty actions list if evidence is insufficient. Do not turn the probe into a full solver.'''

def replay_prefix(source,bad_step):
    env=ScienceWorldAdapter();env.reset(source['spec']['task_name'],source['spec']['variation_id'])
    if digest(env.view)!=digest(source['initial']):env.close();raise RuntimeError('INITIAL_REPLAY_MISMATCH')
    for s in source['steps'][:bad_step-1]:
        env.execute(s['executed_action'])
        if digest(env.view)!=s['observation_hash']:env.close();raise RuntimeError('PREFIX_REPLAY_MISMATCH')
    return env

def run_probe(payload):
    root,mechanism,ref,index,run_id=payload;root=Path(root);rid=run_id+'.'+mechanism['mechanism_id']+'.'+str(index);path=root/'runs-private/probes'/(rid+'.json')
    if path.exists():return read_json(path)
    source=read_json(root/'runs-private/episodes'/(ref['episode_id']+'.json'));step=ref['bad_step'];remaining=min(8,100-step+1)
    env=replay_prefix(source,step);context=env.context();original=source['steps'][step-1]['executed_action'];env.close()
    client=DeepSeekClient(rid,meta={'stage':'local_probe','split':'train'})
    plan,raw,request_id,usage=client.json(PLAN,{'mechanism':mechanism,'source_evidence':ref,'checkpoint':context,'original_action':original,'action_budget':remaining},stage='probe_plan',learning=True)
    actions=plan.get('alternative_actions',[])
    if not isinstance(actions,list) or len(actions)>remaining or any(not isinstance(a,str) or '\n' in a or len(a)>512 for a in actions):actions=[]
    branches=[]
    original_actions=[s['executed_action'] for s in source['steps'][step-1:step-1+remaining]]
    for name,commands in [('original',original_actions),('alternative',actions)]:
        env=replay_prefix(source,step);records=[]
        for action in commands:
            if env.done:break
            before=env.view.copy();env.execute(action)
            records.append({'action':action,'before':before,'after':env.view.copy(),'hash':digest(env.view)})
        branches.append({'name':name,'steps':records,'host_outcome':env.outcome()});env.close()
    alt=branches[1]['steps'];same_action=[s for s in alt if s['action']==original]
    positives=plan.get('positive_feedback_substrings',[]);negatives=plan.get('negative_feedback_substrings',[])
    original_feedback=source['steps'][step-1]['after']['observation']
    evidence={'same_original_action_after_preparation':len(alt)>1 and bool(same_action),'public_feedback_changed':any(s['after']['observation']!=original_feedback for s in same_action),'declared_positive_seen':any(p.lower() in s['after']['observation'].lower() for p in positives if isinstance(p,str) and p for s in alt),'declared_negative_seen':any(p.lower() in s['after']['observation'].lower() for p in negatives if isinstance(p,str) and p for s in alt)}
    result={'probe_id':rid,'mechanism_id':mechanism['mechanism_id'],'source':ref,'plan':plan,'raw_plan':raw,'request_id':request_id,'usage':usage,'prefix_public_hash':digest(context),'prefix_replay_verified':True,'branches':branches,'public_evidence':evidence,'interpretation':'Predeclared substring checks are observable proxy evidence, not task success or causal truth; requires independent DEV confirmation. Host scores are not fed to probe planner.'}
    atomic_json(path,result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--mechanisms',required=True);p.add_argument('--run-id',default='probes-v1');p.add_argument('--all-hypotheses',action='store_true');a=p.parse_args();root=Path(a.root).resolve();ms=read_json(a.mechanisms)['mechanisms']
    # Selection uses TRAIN evidence validity and a fixed SHA tie breaker only.
    selection=read_json(root/'output/artifacts/task_selection.json')
    selected=sorted([m for m in ms if a.all_hypotheses or m['task_name'] in selection['selected_task_types']],key=lambda m:m['mechanism_id']);jobs=[]
    for m in selected:
        refs=m['verified_quote_references'][:2]
        for i,ref in enumerate(refs):jobs.append((str(root),m,ref,i,a.run_id))
    atomic_json(root/'runs-private'/(a.run_id+'.selection.json'),{'mechanisms':selected,'max_alternative_branches_per_mechanism':3,'planned_alternative_branches_per_mechanism':2,'selection':'Two verified TRAIN variation references, fixed mechanism SHA order; no TEST opened.'})
    with ProcessPoolExecutor(max_workers=min(8,max(1,len(jobs))),mp_context=multiprocessing.get_context('spawn')) as pool:results=list(pool.map(run_probe,jobs))
    atomic_json(root/'runs-private'/(a.run_id+'.index.json'),results)
    print(json.dumps({'mechanisms':len(selected),'probes':len(results),'public_effect_evidence':[r['public_evidence'] for r in results]}))
if __name__=='__main__':main()
