import argparse,json
from pathlib import Path
from flowevo_sw.checkpointing import read_json,atomic_json
from flowevo_sw.batch_runner import run_batches

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve();names=read_json(root/'output/artifacts/task_selection.json')['selected_task_types'];rows=[json.loads(l) for l in (root/'data/manifests/train.jsonl').read_text().splitlines()]
    by={n:sorted([r for r in rows if r['task_name']==n],key=lambda r:r['sort_key'])[2:4] for n in names};specs=[by[n][i] for i in range(2) for n in names if i<len(by[n])]
    bank=read_json(root/'runs-private/discovery-v2.F.final_bank.json');summary=[]
    for batch in (1,8):
        rs=run_batches(specs,root/'runs-private',f'batch-sensitivity-{batch}-v1',bank=bank,workers=min(8,len(specs)),batch_size=batch)
        hashes=[r['bank_hash'] for r in rs]
        if batch==8:assert len(set(hashes))==1
        summary.append({'batch_size':batch,'episodes':len(rs),'successes':sum(r.get('outcome',{}).get('success',False) for r in rs),'input_bank_hashes':hashes,'note':'Real repeated TRAIN sensitivity, not independent evaluation. Bank updates are visible only after the declared barrier.'})
    atomic_json(root/'output/artifacts/batch_sensitivity.json',summary)
if __name__=='__main__':main()
