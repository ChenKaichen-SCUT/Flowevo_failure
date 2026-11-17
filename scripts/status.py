import argparse,json,sqlite3
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve();counts={};rows=[]
    for path in sorted((root/'runs-private/episodes').glob('*.json')):
        if '.prefix.' in path.name:continue
        d=json.loads(path.read_text());state=d.get('status');counts[state]=counts.get(state,0)+1
        if state=='EPISODE_LOCKED':rows.append({'job':d['job_id'],'task':d['spec']['task_name'],'score':d['outcome']['final_score'],'success':d['outcome']['success'],'steps':len(d['steps']),'mode':d['trace']['planning_mode'],'error':d['trace']['failure_type']})
        elif state=='MISSING':rows.append({'job':d['job_id'],'error':d['error']})
    print(json.dumps({'counts':counts,'episodes':rows},ensure_ascii=False))
if __name__=='__main__':main()
