"""Literal public-text parsing, shared with every arm; contains no action policy.

Only explicit CURRENT descriptions are parsed. A missing object state is unknown.
No hidden objects, inferred physics, persistent room aliases, or solution rules.
"""
import re

def public_facts(context):
    look=context.get('look','');doors={};containers={}
    for target,state in re.findall(r'A door to the (.+?) \(that is (open|closed)\)',look):doors[target]=state
    for target,state in re.findall(r'The ([^.\n]+?) door is (open|closed)\.',look):containers[target]=state
    location=re.search(r'This room is called the ([^.]+)\.',look)
    return {'location':location.group(1) if location else None,'doors':doors,'containers':containers,'source':'explicit current look only; absent entries are unknown'}

def action_facts(context,action):
    facts=public_facts(context);out={'action_verb':None,'action_target':None,'target_door_state':None,'target_container_state':None}
    for verb in ('go to','look in','open','close','pick up','focus on'):
        if action.startswith(verb+' '):
            target=action[len(verb)+1:];out.update(action_verb=verb,action_target=target)
            if verb in ('go to','open','close') or target.startswith('door to '):out['target_door_state']=facts['doors'].get(target.removeprefix('door to ').removeprefix('the '))
            out['target_container_state']=facts['containers'].get(target)
            break
    return out
