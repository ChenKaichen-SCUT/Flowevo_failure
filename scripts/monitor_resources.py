import argparse,time,json,os
from pathlib import Path
import psutil
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve();path=root/'runs-private/resource_samples.jsonl'
    while not (root/'runs-private/monitor.stop').exists():
        processes=[]
        for proc in psutil.process_iter(['name','memory_info','cpu_times','cmdline']):
            try:
                cmd=' '.join(proc.info['cmdline'] or [])
                if str(root) in cmd or proc.info['name']=='java':processes.append(proc)
            except psutil.Error:pass
        rss=0
        for proc in processes:
            try:rss+=proc.memory_info().rss
            except psutil.Error:pass
        row={'utc_epoch':time.time(),'cpu_percent':psutil.cpu_percent(interval=1),'available_memory':psutil.virtual_memory().available,'experiment_rss':rss,'java_processes':sum(p.name()=='java' for p in processes if p.is_running()),'network_connections':len(psutil.net_connections(kind='tcp'))}
        with path.open('a') as f:f.write(json.dumps(row)+'\n')
        time.sleep(4)
if __name__=='__main__':main()
