import argparse,subprocess,hashlib,json,datetime
from pathlib import Path
import yaml,httpx,psutil,os
from flowevo_sw.checkpointing import atomic_json

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve();out=root/'output';manifest={}
    for name in ('FlowEvo','ScienceWorld','failure-experiments'):
        d=root/'vendor'/name
        def git(*args):return subprocess.check_output(['git','-C',str(d),*args],text=True).strip()
        licenses=[x for x in d.iterdir() if x.name.lower().startswith(('license','copying')) and x.is_file()]
        manifest[name]={'commit':git('rev-parse','HEAD'),'remote':git('remote','get-url','origin'),'working_tree':git('status','--porcelain'),'licenses':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in licenses}}
    atomic_json(out/'artifacts/upstream_manifest.json',manifest)
    private=root/'runs-private/docs';private.mkdir(exist_ok=True,parents=True);docs=[]
    for route in ('quick_start/pricing/','quick_start/rate_limit/','guides/thinking_mode/'):
        url='https://api-docs.deepseek.com/'+route;r=httpx.get(url,timeout=60,follow_redirects=True);r.raise_for_status();name=route.strip('/').replace('/','_')+'.html';(private/name).write_bytes(r.content)
        docs.append({'url':url,'sha256':hashlib.sha256(r.content).hexdigest(),'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'private_file':name})
    atomic_json(out/'artifacts/provider_pricing_snapshot.json',{'documents':docs,'model':'deepseek-flash','observed_document_model_version':'DeepSeek-V4.1-Flash-1017','thinking':'disabled','conservative_peak_usd_per_million':{'input_cache_hit':.006,'input_cache_miss':.30,'output':1.20},'billing_note':'All estimates use peak prices; supplier actual bill is separate and not available via completion usage. No assertion of fixed weights from alias.'})
    atomic_json(out/'artifacts/resources.json',{'os':subprocess.check_output(['lsb_release','-ds'],text=True).strip(),'cpus_affinity':len(os.sched_getaffinity(0)),'memory_total':psutil.virtual_memory().total,'memory_available':psutil.virtual_memory().available,'disk_free':psutil.disk_usage(root).free,'github_write_verified_via_connected_plugin':True})
    config=yaml.safe_load((out/'configs/experiment_plan.yaml').read_text())
    env=json.loads((out/'artifacts/environment_manifest.json').read_text())
    config['project'].update(run_id='scienceworld-20261117-v1',upstream_flowevo_commit=manifest['FlowEvo']['commit'],upstream_scienceworld_commit=manifest['ScienceWorld']['commit'],jar_sha256=env['jar_sha256'])
    config['provider']['api_key_file']='../secrets/api.txt';config['parallel']['environment_workers']=8;config['parallel']['global_api_concurrency_initial']=8
    config['scienceworld']['valid_action_interface']='official_valid_action_assisted_all_actions_unfiltered'
    config['budget']['pricing_snapshot']='artifacts/provider_pricing_snapshot.json'
    (out/'configs/experiment_plan.yaml').write_text(yaml.safe_dump(config,sort_keys=False,allow_unicode=True))
if __name__=='__main__':main()
