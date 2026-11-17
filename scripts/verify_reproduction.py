"""Real JVM replay of autonomously obtained TRAIN actions, without new decisions."""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from alfworld_.schemas import AlfWorldTask,AlfWorldSkillTemplate,AlfWorldExemplar
from flowevo_sw.adapter import ScienceWorldAdapter
from flowevo_sw.action_gateway import ActionGateway
from flowevo_sw.flowevo_adapter import ScienceExecutor
from flowevo_sw.checkpointing import atomic_json,read_json,digest

class ReplayGenerator:
    def __init__(self,adapter,actions):self.adapter=adapter;self.actions=actions;self.last={}
    def step(self,*args,**kwargs):
        action=self.actions[self.adapter.decisions]
        self.last={'raw':json.dumps({'action':action}),'request_id':'OFFLINE_RESPONSE_REPLAY'}
        return SimpleNamespace(action=action,prompt_tokens=0,completion_tokens=0)

def replay(source,mode,arm='F'):
    adapter=ScienceWorldAdapter();view=adapter.reset(source['spec']['task_name'],source['spec']['variation_id'])
    gateway=ActionGateway(adapter,arm=arm,rules=[]);actions=[s['executed_action'] for s in source['steps']]
    gen=ReplayGenerator(adapter,actions);ex=ScienceExecutor(gateway,gen,max_steps=100)
    task=AlfWorldTask('replay',source['spec']['task_name'],view['goal'])
    template=AlfWorldSkillTemplate('engineering_observed_trace',task.task_type,actions if mode=='direct' else actions[:1],[])
    guide=AlfWorldExemplar('engineering_public_trace',task.task_type,task.goal,['Use saved autonomous TRAIN action responses for this engineering replay.'])
    retrieved={'best_layer':1,'template':template,'exemplar':guide} if mode in ('direct','fallback') else {'best_layer':2,'template':None,'exemplar':guide} if mode=='guided' else {}
    trace=ex.run(task,view['observation'],view['valid_actions'],skill_bindings={},skill_library_result=retrieved)
    hashes=[s['observation_hash'] for s in gateway.steps];expected=[s['observation_hash'] for s in source['steps']]
    result={'mode':mode,'arm':arm,'source_job':source['job_id'],'success':trace.success,'direct':trace.direct_use_count,'fallback':trace.fallback_triggered,'guided':trace.skill_seeded,'hashes_match':hashes==expected,'sources':[s['source'] for s in gateway.steps],'outcome':adapter.outcome()}
    adapter.close();return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--run-id',default='discovery-v2');a=p.parse_args();root=Path(a.root).resolve();sources=[]
    for path in sorted((root/'runs-private/episodes').glob(a.run_id+'.F.*.json')):
        if '.prefix.' in path.name:continue
        d=read_json(path)
        if d.get('status')=='EPISODE_LOCKED' and d['outcome']['success'] and all(s['executed_action'] in s['before']['valid_actions'] for s in d['steps']):sources.append(d)
    if not sources:raise RuntimeError('No autonomous successful replay source yet')
    source=min(sources,key=lambda d:len(d['steps']))
    records=[replay(source,m) for m in ('dynamic','guided','direct','fallback')]+[replay(source,'dynamic','F-I')]
    assert all(r['success'] and r['hashes_match'] for r in records)
    atomic_json(root/'output/artifacts/real_replay_verification.json',{'records':records,'interpretation':'Real environment plus recorded autonomous model actions. Engineering only; neither new DeepSeek decisions nor transfer results.'})
    print(json.dumps(records))
if __name__=='__main__':main()
