import argparse,hashlib,json,platform,subprocess
from pathlib import Path
import scienceworld
from scienceworld import ScienceWorldEnv
from scienceworld.constants import JAR_PATH
from flowevo_sw.checkpointing import atomic_json,digest,canonical

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve();out=root/'output';dest=root/'data/manifests';dest.mkdir(parents=True,exist_ok=True)
    jar=Path(JAR_PATH);fingerprint=hashlib.sha256(jar.read_bytes()).hexdigest()
    env=ScienceWorldEnv();names=env.get_task_names();manifests={s:[] for s in ('train','dev','test')}
    for name in names:
        env.load(name,0,simplificationStr='',generateGoldPath=False)
        for split in manifests:
            variations=getattr(env,'get_variations_'+split)()
            for v in variations:
                row={'task_name':name,'variation_id':int(v),'split':split,'jar_sha256':fingerprint,'simplifications':'','episode_limit':100,'manifest_seed':20261117}
                row['episode_id']=digest(row)[:20];row['sort_key']=digest([20261117,name,int(v),split]);manifests[split].append(row)
    env.close();hashes={}
    for split,rows in manifests.items():
        rows.sort(key=lambda x:x['sort_key']);name='test_manifest.private.jsonl' if split=='test' else split+'.jsonl'
        content=''.join(canonical(r)+'\n' for r in rows);(dest/name).write_text(content);hashes[split]=hashlib.sha256(content.encode()).hexdigest()
    atomic_json(dest/'all_tasks.json',names);atomic_json(dest/'split_hashes.json',hashes);(dest/'exclusions.jsonl').write_text('')
    environment={'python':platform.python_version(),'scienceworld_version':scienceworld.__version__,'jar_sha256':fingerprint,'jar_relative_path':'vendor/ScienceWorld/scienceworld/scienceworld.jar','java':subprocess.check_output(['java','-version'],stderr=subprocess.STDOUT,text=True),'tasks':len(names),'splits':{s:len(v) for s,v in manifests.items()}}
    atomic_json(out/'artifacts/environment_manifest.json',environment)
    print(canonical(environment))
if __name__=='__main__':main()
