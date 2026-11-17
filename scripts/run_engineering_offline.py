"""Complete zero-provider workflow; run inside unshare -n with loopback up."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import yaml
from engineering_common import write

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve();out=root/'output'
    config=yaml.safe_load((out/'configs/engineering_zero_api.yaml').read_text())
    assert config['new_model_requests_max']==0 and config['new_api_cost_cny_max']==0
    interfaces=sorted(x['ifname'] for x in json.loads(subprocess.check_output(['ip','-json','link','show'])))
    assert interfaces==config['network_interfaces_allowed']
    env=dict(os.environ);env['FLOWEVO_OFFLINE_ONLY']='1'
    for key in ('DEEPSEEK_API_KEY','OPENAI_API_KEY'):env.pop(key,None)
    def run(script,extra=()):
        command=[sys.executable,str(out/'scripts'/script),'--root',str(root),*extra]
        log=root/(script+'.log')
        with log.open('w',encoding='utf-8') as stream:subprocess.run(command,cwd=out,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
        return {'script':script,'status':'PASSED'}
    with (root/'tests-final.log').open('w',encoding='utf-8') as stream:
        subprocess.run([sys.executable,'-m','pytest','-q','tests'],cwd=out,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    with ThreadPoolExecutor(max_workers=config['static_workers']) as pool:
        results=list(pool.map(run,['engineering_governance.py','engineering_action_audit.py','engineering_binding.py']))
    results.append(run('engineering_jvm_checks.py',['--workers',str(config['jvm_workers'])]))
    write(out/'artifacts/engineering/orchestration.json',{'config':config,'results':results,'interfaces':interfaces,'offline_client_guard':True,'new_model_calls':0})
    print(json.dumps({'status':'PASSED','analysis_jobs':len(results),'new_model_calls':0}))
if __name__=='__main__':main()
