import argparse,hashlib,time,multiprocessing,os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import psutil
from flowevo_sw.adapter import ScienceWorldAdapter
from flowevo_sw.checkpointing import atomic_json,digest,read_json

def replay(job):
    task,variation,actions=job;start=time.time();env=ScienceWorldAdapter();views=[env.reset(task,variation)];initial_moves=env.info['moves'];out=[]
    for a in actions:env.execute(a);views.append(env.view.copy());out.append(env.outcome())
    rss=psutil.Process().memory_info().rss+sum(p.memory_info().rss for p in psutil.Process().children(recursive=True))
    rec={'public_hash':digest(views),'outcome':out[-1] if out else env.outcome(),'seconds':time.time()-start,'rss_bytes':rss,'valid_count':len(views[0]['valid_actions']),'initial_moves':initial_moves}
    env.close();return rec

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve()
    task=read_json(root/'data/manifests/all_tasks.json')[0]
    import json
    rows=[json.loads(l) for l in (root/'data/manifests/train.jsonl').read_text().splitlines()];row=next(r for r in rows if r['task_name']==task)
    job=(task,row['variation_id'],['look around','inventory','wait1','look around'])
    singles=[replay(job),replay(job)];cal=[]
    for workers in [1,2,4,8]:
        start=time.time()
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:records=list(pool.map(replay,[job]*workers))
        cal.append({'workers':workers,'wall_seconds':time.time()-start,'records':records})
    hashes={r['public_hash'] for r in singles+[r for c in cal for r in c['records']]}
    out={'actions':job[2],'task_name':task,'variation_id':row['variation_id'],'singles':singles,'parallel':cal,'deterministic':len(hashes)==1,'cpu_affinity':len(os.sched_getaffinity(0)),'memory_available':psutil.virtual_memory().available,'valid_action_assisted':True,'success_rule':'native getCompleted AND score==100','wrapper_timeout_rule':'moves > envStepLimit','host_decision_limit':100,'gold_generation':False}
    atomic_json(root/'output/artifacts/environment_audit.json',out);print(out)
    if not out['deterministic']:raise RuntimeError('REPLAY_NONDETERMINISTIC')
if __name__=='__main__':main()
