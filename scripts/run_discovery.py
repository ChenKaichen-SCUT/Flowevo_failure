import argparse,json
from pathlib import Path
from flowevo_sw.batch_runner import run_batches
from flowevo_sw.checkpointing import read_json,atomic_json

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--workers',type=int,default=8);p.add_argument('--run-id',default='discovery-v1');p.add_argument('--per-type',type=int,default=2);p.add_argument('--batch-size',type=int,default=8);p.add_argument('--task');p.add_argument('--bank');p.add_argument('--limit',type=int,default=100);a=p.parse_args();root=Path(a.root).resolve()
    rows=[json.loads(l) for l in (root/'data/manifests/train.jsonl').read_text().splitlines()]
    names=read_json(root/'data/manifests/all_tasks.json');by={n:sorted([r for r in rows if r['task_name']==n],key=lambda r:r['sort_key']) for n in names}
    if a.task:names=[a.task]
    selected=[by[n][i] for i in range(a.per_type) for n in names if i<len(by[n])]
    run_batches(selected,root/'runs-private',a.run_id,bank=read_json(a.bank) if a.bank else None,workers=a.workers,batch_size=a.batch_size,limit=a.limit)
if __name__=='__main__':main()
