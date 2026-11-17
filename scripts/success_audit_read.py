"""Lossless action/feedback reader with changed public-state lines for review."""
import argparse,json
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('patterns',nargs='+');p.add_argument('--packets',default='artifacts/success_audit/source_packets');a=p.parse_args()
for path in sorted(Path(a.packets).glob('*.json')):
    if not any(x in path.name for x in a.patterns):continue
    d=json.loads(path.read_text(encoding='utf-8'));print('\n###',path.stem,'\n',d['goal'],'\nINITIAL LOOK',d['initial']['look'],'INVENTORY',d['initial']['inventory'])
    for s in d['steps']:
        try:reason=json.loads(s.get('raw_model_response') or '{}').get('reason','')
        except (ValueError,TypeError):reason=s.get('raw_model_response') or ''
        observation=s['after']['observation']
        if observation.strip()==s['after']['look'].strip():observation='[room description identical to current look; changes below]'
        print('STEP',s['step'],s['executed_action'],'\nREASON',reason,'\nFEEDBACK',observation)
        for field in ('look','inventory'):
            before=s['before'][field].splitlines();after=s['after'][field].splitlines()
            removed=[l for l in before if l not in after];added=[l for l in after if l not in before]
            if removed or added:print(field.upper(),'REMOVED',removed,'ADDED',added)
