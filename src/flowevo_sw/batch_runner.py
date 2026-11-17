import os,time,json,copy,multiprocessing,random
from pathlib import Path
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor
from alfworld_.schemas import AlfWorldTrace,AlfWorldAction,AlfWorldTask
from alfworld_.skill_library import SkillLibrary
from .adapter import ScienceWorldAdapter
from .action_gateway import ActionGateway
from .flowevo_adapter import ScienceExecutor,ScienceGenerator,ScienceCompiler,bind_skill,public_episode
from .deepseek_client import DeepSeekClient
from .checkpointing import atomic_json,read_json,digest

_env=None
def init_worker(limit):
    global _env
    _env=ScienceWorldAdapter(limit)

def run_episode(payload):
    spec,bank,arm,rules,root,run_id=payload
    jid=f"{run_id}.{arm}.{spec['episode_id']}";path=Path(root)/'episodes'/(jid+'.json')
    if path.exists():
        old=read_json(path)
        if old.get('status')=='EPISODE_LOCKED':return old
    started=time.time();atomic_json(path,{'status':'STARTED','job_id':jid,'spec':spec})
    client=DeepSeekClient(jid,meta={'run':run_id,'arm':arm,'episode':spec['episode_id'],'split':spec['split']})
    global _env
    try:
        view=_env.reset(spec['task_name'],spec['variation_id'])
        lib=SkillLibrary.from_dict(copy.deepcopy(bank));retrieved=lib.retrieve(spec['task_name']);bindings=None;binding_event=None
        if spec.get('native_holdout',False):
            retrieved['exemplar']=None;retrieved['insight']=None
            retrieved['best_layer']=1 if retrieved['template'] else None
        if retrieved['template'] is not None:bindings,binding_event=bind_skill(client,retrieved['template'],view)
        gateway=ActionGateway(_env,client,arm,rules)
        prefix_path=path.with_suffix('.prefix.json')
        saved=read_json(prefix_path) if prefix_path.exists() else []
        def checkpoint(steps):
            i=len(steps)-1
            if i<len(saved) and (steps[i]['observation_hash']!=saved[i]['observation_hash'] or steps[i]['executed_action']!=saved[i]['executed_action']):raise RuntimeError('RECOVERY_REPLAY_MISMATCH')
            if len(steps)>=len(saved):atomic_json(prefix_path,steps)
        gateway.checkpoint=checkpoint
        generator=ScienceGenerator(client,_env);executor=ScienceExecutor(gateway,generator,max_steps=_env.limit)
        task=AlfWorldTask(spec['episode_id'],spec['task_name'],view['goal'],benchmark='scienceworld')
        trace=executor.run(task,view['observation'],view['valid_actions'],skill_bindings=bindings,skill_library_result=retrieved)
        trace.trace_id=jid;trace.benchmark='scienceworld';trace.strategy_holdout=spec.get('native_holdout',False)
        result={'status':'EPISODE_LOCKED','job_id':jid,'run_id':run_id,'arm':arm,'spec':spec,'initial':_env.initial,'outcome':_env.outcome(),'trace':asdict(trace),'steps':gateway.steps,'checks':gateway.checks,'binding':binding_event,'retrieved':{k:(v.to_dict() if hasattr(v,'to_dict') else v) for k,v in retrieved.items()},'bank_hash':digest(bank),'requests':client.records,'wall_seconds':time.time()-started}
    except Exception as exc:
        result={'status':'MISSING','job_id':jid,'run_id':run_id,'arm':arm,'spec':spec,'error':type(exc).__name__+': '+str(exc)[:300],'requests':client.records,'wall_seconds':time.time()-started}
    atomic_json(path,result);return result

def compile_result(result):
    if result['status']!='EPISODE_LOCKED' or not result['outcome']['success']:return None
    client=DeepSeekClient(result['job_id']+'.compile',meta={'run':result['run_id'],'arm':result['arm'],'episode':result['spec']['episode_id']})
    trace=restore_trace(result);compiler=ScienceCompiler(client,public_episode(result))
    try:
        c=compiler.compile(trace)
        return {'job_id':result['job_id'],'template':c.template.to_dict() if c.template else None,'exemplar':c.exemplar.to_dict() if c.exemplar else None,'rejection':compiler.rejection,'raw_parsed':compiler.generated,'requests':client.records}
    except Exception as exc:return {'job_id':result['job_id'],'error':type(exc).__name__+': '+str(exc)[:200],'requests':client.records}

def restore_trace(result):
    d=copy.deepcopy(result['trace']);d['actions']=[AlfWorldAction(**a) for a in d['actions']]
    return AlfWorldTrace(**d)

def publish_batch(lib,results,compiled):
    from alfworld_.schemas import AlfWorldSkillTemplate,AlfWorldExemplar
    events=[]
    for r,c in zip(results,compiled):
        if r['status']!='EPISODE_LOCKED':continue
        trace=restore_trace(r);lib.advance_episode();before=lib.to_dict()
        template=r.get('retrieved',{}).get('template')
        if template and r['retrieved'].get('best_layer')==1:lib.record_template_usage(template['template_id'],trace.success)
        if trace.strategy_holdout:lib.record_unguided(trace.task_type,trace.success)
        elif trace.planning_mode in ('exemplar_guided','insight_guided','direct_then_exemplar','direct_then_insight'):lib.record_guided(trace.task_type,trace.success)
        lib.record_trace_stats(trace)
        admitted=False
        if c and c.get('template'):admitted=lib.add_template(AlfWorldSkillTemplate.from_dict(c['template']))
        if c and c.get('exemplar'):lib.add_exemplar(AlfWorldExemplar.from_dict(c['exemplar']))
        audit=lib.periodic_audit() if lib._current_episode%20==0 else {'not_due':True}
        events.append({'job_id':r['job_id'],'compiled':bool(c),'admitted':admitted,'audit':audit,'before_hash':digest(before),'after_hash':digest(lib.to_dict()),'status_before':before['template_status'],'status_after':lib.to_dict()['template_status']})
    return events

def run_batches(specs,root,run_id,bank=None,arms=None,rules=None,workers=8,batch_size=8,limit=100):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);arms=arms or ['F'];rules=rules or {}
    plan_path=root/(run_id+'.plan.json')
    plan={'specs':specs,'arms':arms,'rules':rules,'initial_bank_hash':digest(bank or {}),'workers':workers,'batch_size':batch_size,'limit':limit}
    if plan_path.exists() and read_json(plan_path)!=plan:raise ValueError('Frozen plan mismatch')
    atomic_json(plan_path,plan)
    banks={a:SkillLibrary.from_dict(copy.deepcopy(bank or {})) for a in arms}
    all_results=[];ctx=multiprocessing.get_context('spawn');rngs={a:random.Random(1337) for a in arms}
    for start in range(0,len(specs),batch_size):
        batch=specs[start:start+batch_size];snap={a:banks[a].to_dict() for a in arms}
        # New workers each batch: independent JVMs, no cross-batch heap growth.
        jobs=[]
        for s in batch:
            for a in arms:
                retrieved=banks[a].retrieve(s['task_name'])
                eligible=retrieved['exemplar'] is not None or retrieved['insight'] is not None
                spec=dict(s,native_holdout=(rngs[a].random()<.20 if eligible else False))
                jobs.append((spec,snap[a],a,rules.get(a,[]),str(root),run_id))
        with ProcessPoolExecutor(max_workers=workers,mp_context=ctx,initializer=init_worker,initargs=(limit,)) as pool:
            results=list(pool.map(run_episode,jobs))
        # Compilation is parallel, but publishing follows frozen task order.
        compiled=[]
        def compile_saved(r):
            p=root/'compilations'/(r['job_id']+'.json')
            if p.exists():return read_json(p)
            c=compile_result(r);atomic_json(p,c);return c
        with ThreadPoolExecutor(max_workers=workers) as pool:compiled=list(pool.map(compile_saved,results))
        for a in arms:
            idx=[i for i,r in enumerate(results) if r['arm']==a]
            ev=publish_batch(banks[a],[results[i] for i in idx],[compiled[i] for i in idx])
            atomic_json(root/'banks'/f'{run_id}.{a}.batch{start//batch_size:03d}.json',{'library':banks[a].to_dict(),'events':ev,'input_hash':digest(snap[a])})
        all_results+=results
        print(json.dumps({'run':run_id,'completed':len(all_results),'successes':sum(r.get('outcome',{}).get('success',False) for r in all_results),'missing':sum(r['status']=='MISSING' for r in all_results),'banks':{a:lib.snapshot() for a,lib in banks.items()}},ensure_ascii=False),flush=True)
        if (root/(run_id+'.stop_requested')).exists() or any(r['status']=='MISSING' or 'BUDGET_EXHAUSTED' in r.get('trace',{}).get('failure_type','') or 'UNKNOWN' in r.get('trace',{}).get('failure_type','') for r in results):
            atomic_json(root/(run_id+'.stop.json'),{'reason':'INCOMPLETE_PAIRED_BLOCK_OR_INFRASTRUCTURE','batch_start':start});break
    for a,lib in banks.items():atomic_json(root/(run_id+'.'+a+'.final_bank.json'),lib.to_dict())
    return all_results
