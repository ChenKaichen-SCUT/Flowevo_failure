import argparse,time,statistics
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from flowevo_sw.deepseek_client import DeepSeekClient
from flowevo_sw.checkpointing import atomic_json

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--run-id',default='calibration-ladder-v2');a=p.parse_args();root=Path(a.root).resolve();records=[]
    for round_index,concurrency in enumerate((8,16,8)):
        def ping(i):
            c=DeepSeekClient(f'{a.run_id}.r{round_index}.{i}',meta={'stage':'parallel_calibration'});t=time.monotonic()
            raw,rid,u=c.call('Transport calibration only. Reply OK.','OK');c.parsed(rid,'CALIBRATION')
            return {'latency':time.monotonic()-t,'request_id':rid,'usage':u}
        started=time.monotonic()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:responses=list(pool.map(ping,range(32)))
        wall=time.monotonic()-started;records.append({'concurrency':concurrency,'requests':32,'wall_seconds':wall,'requests_per_second':32/wall,'responses':responses})
    baseline=statistics.mean(r['requests_per_second'] for r in records if r['concurrency']==8);higher=records[1]['requests_per_second'];chosen=16 if higher>baseline*1.10 else 8
    atomic_json(root/'output/artifacts/api_ladder.json',{'rounds':records,'selected':chosen,'gain_ratio':higher/baseline,'ready_demand':'Formal batch has up to 40 independent success compilations; environment pool remains 8. Escalation beyond 16 is not justified by ready demand.','criteria':'Same 32 solution-free calls per rung; require >10% throughput gain and no errors.'});print({'selected':chosen,'gain_ratio':higher/baseline})
if __name__=='__main__':main()
