"""Build source-only packets before compiler review; no model/runtime imports."""
import argparse,collections,hashlib,json
from pathlib import Path

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(value):return hashlib.sha256(value).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')

def verify_frozen(out,files):
    # Windows review files and Linux regeneration may differ only in line ends.
    # Check the published byte digest against both encodings; never re-label.
    for name,expected in files.items():
        body=(Path(out)/name).read_bytes();lf=body.replace(b'\r\n',b'\n')
        assert expected in {sha(body),sha(lf),sha(lf.replace(b'\n',b'\r\n'))},name

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    inp=Path(a.input).resolve();out=Path(a.output).resolve();cfg=read(out/'configs/success_trace_audit.json')
    inventory=[];packets=[];primary={};allcounts=collections.Counter()
    for f in sorted((inp/'episodes').glob('*.json')):
        if '.prefix.' in f.name:continue
        e=read(f);allcounts[(e['run_id'],e['arm'],e['spec']['split'])]+=1
        if not e['trace']['success']:continue
        assert e['outcome']['success'] and e['steps'][-1]['host_outcome']['success']
        unit=e['spec']['task_name']+':'+str(e['spec']['variation_id'])
        scope=('PRIMARY_TRAIN_DEV' if e['run_id'] in cfg['primary_runs'] and e['arm']==cfg['primary_arm'] and e['spec']['split'] in cfg['primary_splits'] else
               'SUPPLEMENTARY_TRAIN_VERSION' if e['spec']['split'] in ('train','dev') else 'HISTORICAL_TEST_ONLY')
        row={'job_id':e['job_id'],'episode_id':e['spec']['episode_id'],'run':e['run_id'],'arm':e['arm'],'split':e['spec']['split'],
             'task':e['spec']['task_name'],'variation':e['spec']['variation_id'],'unit':unit,'scope':scope,
             'steps':len(e['steps']),'host_success_confirmed':True,'source_ref':'episodes/'+f.name,
             'source_sha256':sha(f.read_bytes()),'episode_semantic_sha256':sha(canonical(e))}
        inventory.append(row)
        if scope=='HISTORICAL_TEST_ONLY':continue
        packet={'identity':row,'goal':e['initial']['goal'],'initial':e['initial'],
          'steps':[{k:s[k] for k in ('step','source','executed_action','parsed_action','raw_model_response','before','after','request_id') if k in s} for s in e['steps']]}
        write(out/'artifacts/success_audit/source_packets'/(e['job_id']+'.json'),packet)
        lines=['# '+e['job_id'],row['task']+' | '+row['split']+' | variation '+str(row['variation']),e['initial']['goal'],
               'INITIAL LOOK: '+e['initial']['look'],'INITIAL INVENTORY: '+e['initial']['inventory']]
        for s in packet['steps']:
            try:reason=json.loads(s.get('raw_model_response') or '{}').get('reason','')
            except (TypeError,ValueError):reason=s.get('raw_model_response') or ''
            lines+=['\nSTEP '+str(s['step'])+' ['+s['source']+'] '+s['executed_action'],'REASON: '+reason,'FEEDBACK: '+s['after']['observation']]
            for key in ('look','inventory'):
                if s['after'][key]!=s['before'][key]:lines.append(key.upper()+': '+s['after'][key])
        text='\n'.join(lines)+'\n'
        (out/'artifacts/success_audit/source_packets'/(e['job_id']+'.txt')).write_text(text,encoding='utf-8')
        packets.append({'job_id':e['job_id'],'packet_sha256':sha(canonical(packet)),'text_sha256':sha(text.encode()),'scope':scope,'unit':unit})
        if scope=='PRIMARY_TRAIN_DEV':primary.setdefault(unit,[]).append(row)
    representatives={unit:sorted(rows,key=lambda r:(cfg['primary_runs'].index(r['run']),r['job_id']))[0]['job_id'] for unit,rows in primary.items()}
    write(out/'artifacts/success_audit/success_inventory.json',inventory)
    write(out/'artifacts/success_audit/source_manifest.json',{'packets':packets,'primary_representatives':representatives,
      'config_sha256':sha((out/'configs/success_trace_audit.json').read_bytes()),'compiler_files_read':False,'new_model_calls':0,
      'record_counts':[{'run':k[0],'arm':k[1],'split':k[2],'records':v} for k,v in sorted(allcounts.items())]})
    print(json.dumps({'success_records':len(inventory),'scopes':dict(collections.Counter(r['scope'] for r in inventory)),
                     'primary_units':len(primary),'primary_duplicate_groups':{k:len(v) for k,v in primary.items() if len(v)>1},'source_only_packets':len(packets)},ensure_ascii=False))
    for row in inventory:
        if row['scope']!='HISTORICAL_TEST_ONLY':print(row['job_id'],row['task'],row['variation'],row['steps'],row['scope'])

if __name__=='__main__':main()
