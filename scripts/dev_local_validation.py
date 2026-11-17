"""Real DEV interventions at a predeclared grid; scores never drive planning."""
import argparse,json,multiprocessing,re,copy
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from flowevo_sw.checkpointing import read_json,atomic_json,digest
from flowevo_sw.invariant_runtime import check
from flowevo_sw.deepseek_client import DeepSeekClient
from flowevo_sw.adapter import ScienceWorldAdapter
from flowevo_sw.action_gateway import ActionGateway,Veto
from flowevo_sw.flowevo_adapter import ScienceGenerator
from alfworld_.skill_library import SkillLibrary
from flowevo_sw.shared_state import public_facts

GRID=[0,4,8,12,24,48,72]
FAIL=re.compile(r"isn't open|door is not open|already open|no known action|don't understand|cannot|can't",re.I)

def human_rules():
    common={'version':1,'source_evidence_ids':['TRAIN_PUBLIC_PRECONDITION_AUDIT'],'scope':'Explicit currently closed target only','public_state_requirements':['explicit current look'],'protected_property':'perform an operation only with an explicitly open access path','invalidation':'Use current look only; unknown or changed state releases the veto','exceptions':['unknown state','waiting','closing or reversing state'],'on_unknown':'ABSTAIN','counterexamples':[],'validation_status':'CANDIDATE','authorship':'HUMAN_MINIMAL_BASELINE_NOT_AUTONOMOUS'}
    return [dict(common,rule_id='human_closed_door',trigger={'all':[{'eq':['action_verb','go to']},{'eq':['target_door_state','closed']}]}),dict(common,rule_id='human_closed_container',trigger={'all':[{'eq':['action_verb','look in']},{'eq':['target_container_state','closed']}]})]

def prefix(source,n):
    e=ScienceWorldAdapter();e.reset(source['spec']['task_name'],source['spec']['variation_id'])
    for s in source['steps'][:n]:
        e.execute(s['executed_action'])
        if digest(e.view)!=s['observation_hash']:e.close();raise RuntimeError('DEV_PREFIX_MISMATCH')
    return e

def run_case(job):
    root,case,arm,rules,bank,run_id=job;root=Path(root);jid=run_id+'.'+case['case_id']+'.'+arm;path=root/'runs-private/dev_local'/(jid+'.json')
    if path.exists():return read_json(path)
    source=read_json(root/'runs-private/episodes'/(case['source_job']+'.json'));env=prefix(source,case['prefix_len']);client=DeepSeekClient(jid,meta={'run':run_id,'arm':arm,'split':'dev','stage':'local_diagnostic'})
    gateway=ActionGateway(env,client,arm,rules);gen=ScienceGenerator(client,env);lib=SkillLibrary.from_dict(bank);retrieved=lib.retrieve(source['spec']['task_name']);guide=retrieved['exemplar'].to_prompt_text() if retrieved['exemplar'] else ''
    original=case['action'];start_view=env.view.copy();start_hash=digest(env.view);max_actions=min(8,100-case['prefix_len']);failure=None
    directives=['Controlled local DEV probe: the currently proposed local interaction is '+original+'. Use public feedback to establish any necessary public precondition and complete this local interaction. If the requested condition is already satisfied, continue toward the stated overall task goal.']
    for local in range(max_actions):
        if env.done:break
        correction=None
        for attempt in range(2):
            try:
                if local==0 and attempt==0:action=original;metadata={}
                else:
                    out=gen.step(env.view['goal'],env.view['observation'],env.view['valid_actions'],skill_context=guide,policy_directives=directives,correction=correction);action=out.action;metadata=gen.last
                receipt=gateway.step(action,source='frozen_dev_proposal' if local==0 and attempt==0 else 'local_replan',replanned=attempt>0,**metadata)
                break
            except Veto as exc:
                correction='Public-state constraint rejected the proposed action; one replan is available: '+str(exc)
                if attempt:failure='PERSISTENT_CONSTRAINT_CONFLICT'
            except Exception as exc:failure=type(exc).__name__+': '+str(exc)[:200];break
        if failure:break
        if action==original and not FAIL.search(receipt.observation):break
    result={'case':case,'arm':arm,'job_id':jid,'prefix_hash':start_hash,'start_view':start_view,'steps':gateway.steps,'checks':gateway.checks,'error':failure,'requests':client.records,'host_outcome':env.outcome()};env.close();atomic_json(path,result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--bank',required=True);p.add_argument('--dev-run',default='dev-baseline-v1');p.add_argument('--run-id',default='dev-local-v2');a=p.parse_args();root=Path(a.root).resolve();bank=read_json(a.bank);candidates=read_json(root/'output/artifacts/candidate_rules.json');sources=[]
    for f in sorted((root/'runs-private/episodes').glob(a.dev_run+'.F.*.json')):
        if '.prefix.' not in f.name:
            d=read_json(f)
            if d.get('status')=='EPISODE_LOCKED':sources.append(d)
    humans=human_rules();atomic_json(root/'output/artifacts/human_rules.json',humans)
    cases=[]
    for c in candidates:
        rule=c.get('rule')
        if not rule:continue
        selected=[]
        for source in sorted(sources,key=lambda s:digest([20261117,'dev-checkpoint',s['job_id']])):
            found=None
            for n in GRID:
                if n>=len(source['steps']):continue
                view=source['initial'] if n==0 else source['steps'][n-1]['after']
                hist=[{'action':s['executed_action'],'feedback':s['after']['observation']} for s in source['steps'][:n]]
                context=dict(view,history=hist)
                # The valid-action API filters preconditions; a state constraint must
                # also be tested on syntactically supported but currently invalid acts.
                # Enumerate only public referents and generic interface grammar.
                facts=public_facts(view);universe=set(view['valid_actions'])
                universe.add(source['steps'][n]['executed_action'])
                for target in facts['doors']:
                    universe.update(['go to '+target,'go to door to '+target,'open door to '+target,'close door to '+target])
                for target in facts['containers']:
                    universe.update(['look in '+target,'open '+target,'close '+target])
                actions=sorted(universe,key=lambda ac:digest([20261117,ac]))
                action=next((ac for ac in actions if check(rule,context,ac)['decision']=='VETO'),None)
                if action:
                    found={'rule_id':rule['rule_id'],'candidate_arm':c['arm'],'source_job':source['job_id'],'prefix_len':n,'action':action,'variation_id':source['spec']['variation_id'],'task_name':source['spec']['task_name'],'case_origin':'CONTROLLED_REAL_STATE_NOT_NATURAL_PROPOSAL'};found['case_id']=digest(found)[:16];break
            if found:selected.append(found)
            if len(selected)>=2:break
        cases+=selected
    frozen={'grid':GRID,'cases':cases,'selection':'First two independent DEV episode states per rule in fixed SHA order; first triggering action from actual proposal plus syntactic grammar grounded in explicitly visible doors/containers, in fixed SHA order. Includes currently invalid actions. No score or outcome consulted.','bank_hash':digest(bank)}
    atomic_json(root/'output/artifacts'/(a.run_id+'.checkpoint_plan.json'),frozen)
    jobs=[]
    for case in cases:
        candidate=next(c['rule'] for c in candidates if c.get('rule') and c['rule']['rule_id']==case['rule_id'])
        arms=['F','F-I','F-T','F-H'] if case['candidate_arm']=='F-I' else ['F','F-S']
        for arm in arms:jobs.append((str(root),case,arm,humans if arm=='F-H' else [] if arm=='F' else [candidate],bank,a.run_id))
    with ProcessPoolExecutor(max_workers=min(8,max(1,len(jobs))),mp_context=multiprocessing.get_context('spawn')) as pool:results=list(pool.map(run_case,jobs))
    admitted={'F-I':[],'F-S':[]};checks=[]
    for c in candidates:
        r=c.get('rule')
        if not r:continue
        evidence=[]
        for case in [x for x in cases if x['rule_id']==r['rule_id']]:
            base=next(d for d in results if d['case']['case_id']==case['case_id'] and d['arm']=='F');treated=next(d for d in results if d['case']['case_id']==case['case_id'] and d['arm']==c['arm'])
            first=base['steps'][0]['after']['observation'] if base['steps'] else ''
            unknown=check(r,{'look':'','history':[]},case['action'])['decision']=='ABSTAIN'
            allowed_wait=check(r,dict(base['start_view'],history=[]),'wait')['decision']!='VETO'
            allowed_undo=check(r,dict(base['start_view'],history=[]),'close door to hallway')['decision']!='VETO'
            release=[]
            for s in base['steps']:
                verdict=check(r,dict(s['before'],history=[]),s['executed_action'])['decision']
                if not FAIL.search(s['after']['observation']):release.append(verdict!='VETO')
            altered=bool(treated['steps'] and treated['steps'][0]['executed_action']!=case['action'])
            first_veto=any(v.get('decision')=='VETO' for v in treated['checks'][0]['verdicts']) if treated['checks'] else False
            positive=bool(FAIL.search(first)) and first_veto and altered and not treated['error']
            evidence.append({'case_id':case['case_id'],'original_feedback':first,'real_local_intervention':positive,'unknown_abstains':unknown,'wait_not_vetoed':allowed_wait,'undo_not_vetoed':allowed_undo,'accepted_action_release':bool(release) and all(release),'treated_error':treated['error'],'scope':'Local public action error/redundancy avoidance, not full task success.'})
        ok=len(evidence)>=2 and all(e['real_local_intervention'] and e['unknown_abstains'] and e['wait_not_vetoed'] and e['undo_not_vetoed'] and e['accepted_action_release'] for e in evidence)
        checks.append({'rule_id':r['rule_id'],'arm':c['arm'],'admitted':ok,'evidence':evidence})
        if ok:rr=copy.deepcopy(r);rr['validation_status']='VALIDATED';rr['counterexamples']=[e['case_id'] for e in evidence];admitted[c['arm']].append(rr)
    admitted={a:rs[:3] for a,rs in admitted.items()};admitted['F-T']=copy.deepcopy(admitted['F-I'])
    fields=' '.join(json.dumps(r['trigger']) for r in admitted['F-I'])
    admitted['F-H']=[dict(r,validation_status='VALIDATED') for r in humans if ('target_door_state' in json.dumps(r['trigger']) and 'target_door_state' in fields) or ('target_container_state' in json.dumps(r['trigger']) and 'target_container_state' in fields)]
    validation={'status':'VALIDATED' if admitted['F-I'] else 'NO_VALIDATED_CANDIDATE','rules':admitted,'checks':checks,'local_results':results,'caveat':'Controlled interventions establish local functionality. These are not estimates of natural false-veto rates or whole-episode efficacy.'}
    atomic_json(root/'output/artifacts'/(a.run_id+'.validation.json'),validation);atomic_json(root/'output/artifacts/dev_validation.json',validation);print(json.dumps({'status':validation['status'],'admitted_counts':{a:len(v) for a,v in admitted.items()},'checks':checks}))
if __name__=='__main__':main()
