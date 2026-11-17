import argparse,time,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import httpx
from flowevo_sw.deepseek_client import DeepSeekClient
from flowevo_sw.checkpointing import atomic_json

def ping(i):
    c=DeepSeekClient('calibration-v1-'+str(i));start=time.time()
    raw,rid,u=c.call('This is a transport calibration request. Reply only OK.','OK')
    c.parsed(rid,'CALIBRATION');return {'latency':time.time()-start,'usage':u,'request_id':rid,'response':raw}
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve()
    t=time.time()
    with ThreadPoolExecutor(max_workers=8) as pool:r=list(pool.map(ping,range(8)))
    elapsed=time.time()-t
    atomic_json(root/'output/artifacts/api_calibration.json',{'concurrency':8,'ready_requests':8,'wall_seconds':elapsed,'requests':r,'throughput':len(r)/elapsed,'decision':'4 CPUs permit at most 8 environment workers in API-bound mode; no independent ready pool above 8 in TRAIN. Retain API cap 8 until measured larger demand.'})
    print({'requests':len(r),'wall_seconds':elapsed})
if __name__=='__main__':main()
