import argparse,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from flowevo_sw.contrastive_learner import diagnose_group
from flowevo_sw.checkpointing import atomic_json,read_json

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--discovery-run',default='discovery-v1');p.add_argument('--run-id',default='learning-v1');a=p.parse_args();root=Path(a.root).resolve();groups={}
    for f in sorted((root/'runs-private/episodes').glob(a.discovery_run+'.F.*.json')):
        if '.prefix.' in f.name:continue
        r=read_json(f)
        if r['status']=='EPISODE_LOCKED':groups.setdefault(r['spec']['task_name'],[]).append(r)
    def work(item):
        name,results=item;path=root/'runs-private/diagnoses'/(a.run_id+'.'+name+'.json')
        if path.exists():return read_json(path)
        d=diagnose_group(name,results,a.run_id);atomic_json(path,d);return d
    with ThreadPoolExecutor(max_workers=8) as pool:diagnoses=list(pool.map(work,sorted(groups.items())))
    mechanisms=[dict(m,task_name=d['task_name']) for d in diagnoses for m in d['mechanisms'] if m['two_variations_supported']]
    atomic_json(root/'runs-private'/(a.run_id+'.mechanisms.json'),{'mechanisms':mechanisms,'task_count':len(groups),'status':'HYPOTHESES_REQUIRE_PROBES' if mechanisms else 'NO_TWO_VARIATION_HYPOTHESIS'})
    print(json.dumps({'diagnosed_tasks':len(groups),'two_variation_hypotheses':len(mechanisms)}))
if __name__=='__main__':main()
