"""Small auditable representation repairs and three-valued public binding checks.

No material rankings, target answers, scores, or variation IDs. Natural-language
conditions that this version cannot prove remain UNKNOWN, never silently true.
"""
import functools,re
from .checkpointing import digest
from .shared_state import public_facts
from .skill_contracts import ScienceSkillTemplate

def roles(template,source_goal=''):
    result={p:set() for p in template.parameters}
    comparative=bool(re.search(r'least|most|longest|shortest|above|below',source_goal,re.I))
    for action in template.action_template:
        for param in re.findall(r'\{(\w+)\}',action):
            if action.startswith('go to ') or action.startswith('open door to '):role='navigation_destination'
            elif action.startswith('focus on '):
                value=template.example_bindings.get(param,'')
                explicit_marker=bool(value and re.search(r'(?:first|next),?\s+focus on (?:the )?'+re.escape(value),source_goal,re.I))
                role='instrument' if 'instrument' in param or value=='thermometer' else 'goal_choice' if comparative and not explicit_marker else 'goal_marker'
            elif action.startswith(('look at ','use ','connect ')):role='experiment_subject'
            elif action.startswith('move ') and action.endswith('{'+param+'}'):role='transfer_destination'
            else:role='manipulated_object'
            result[param].add(role)
    return {p:sorted(values) for p,values in result.items()}

def source_valid(template,source_actions):
    if set(re.findall(r'\{(\w+)\}',' '.join(template.action_template)))!=set(template.parameters):return False
    if any(not isinstance(template.example_bindings.get(p),str) for p in template.parameters):return False
    iterator=iter(source_actions)
    return all(any(actual==candidate for actual in iterator) for candidate in template.instantiate(template.example_bindings))

def unique_source_alignment(actions,source_actions):
    matches=[]
    for action in actions:
        pieces=re.split(r'(\{\w+\})',action);names=[];pattern=''
        for piece in pieces:
            if re.fullmatch(r'\{\w+\}',piece):names.append(piece[1:-1]);pattern+='(.+?)'
            else:pattern+=re.escape(piece)
        matches.append([(i,list(zip(names,m.groups()))) for i,actual in enumerate(source_actions) if (m:=re.fullmatch(pattern,actual))])
    @functools.lru_cache(None)
    def search(position,start):
        if position==len(actions):return ((),)
        answers=[]
        for index,pairs in matches[position]:
            if index<start:continue
            for tail in search(position+1,index+1):
                answers.append(((index,tuple(pairs)),)+tail)
                if len(answers)>=2:return tuple(answers)
        return tuple(answers)
    candidates=search(0,0)
    return (list(candidates[0]) if len(candidates)==1 else None),len(candidates)

def repair_source_parameters(generated,source_actions,task_type,source_id,source_goal):
    actions=generated.get('action_template',[])
    alignment,count=unique_source_alignment(actions,source_actions)
    if alignment is None:return None,{'status':'AMBIGUOUS_ALIGNMENT' if count else 'NO_SOURCE_ALIGNMENT','alignment_count_capped_at_2':count}
    values={};new_actions=[];bindings={}
    for action,(_,pairs) in zip(actions,alignment):
        by_name=dict(pairs)
        for name,value in pairs:
            values.setdefault(name,[])
            if value not in values[name]:values[name].append(value)
    for action,(_,pairs) in zip(actions,alignment):
        sequence=iter(pairs)
        def substitute(match):
            name,value=next(sequence)
            renamed=name if len(values[name])==1 else name+'_'+str(values[name].index(value)+1)
            bindings[renamed]=value;return '{'+renamed+'}'
        new_actions.append(re.sub(r'\{\w+\}',substitute,action))
    template=ScienceSkillTemplate('repair_'+digest([new_actions,bindings])[:16],task_type,new_actions,list(bindings),bindings,source_trace_id=source_id,
        applicability=generated.get('applicability',''),source_contract={'source_goal':source_goal,'repair':'unique alignment and distinct literal source values; aliases are not silently unified'})
    template.parameter_roles=roles(template,source_goal)
    assert source_valid(template,source_actions)
    return template,{'status':'SOURCE_VALID_CANDIDATE','aligned_source_indices':[x[0] for x in alignment],
        'split_parameters':{p:v for p,v in values.items() if len(v)>1},'transfer_verified':False}

def lift_literal_experiment_object(template,source_actions):
    data=template.to_dict();actions=list(data['action_template']);literals=[]
    for action in actions:
        match=re.fullmatch(r'connect ([^{}]+) to \{\w+\}',action)
        if match:literals.append(match.group(1))
    if len(set(literals))!=1:return None
    literal=literals[0];parameter='experiment_object'
    if parameter in data['parameters']:return None
    data['action_template']=[a.replace('connect '+literal+' to ','connect {'+parameter+'} to ') for a in actions]
    data['parameters'].append(parameter);data['example_bindings'][parameter]=literal
    data['source_contract']=dict(data.get('source_contract',{}),lifted_literal_constraints={parameter:literal})
    data['template_id']='lift_'+digest(data['action_template'])[:16]
    repaired=ScienceSkillTemplate.from_dict(data);repaired.parameter_roles=roles(repaired,data.get('source_contract',{}).get('source_goal',''))
    assert source_valid(repaired,source_actions)
    return repaired

def preparation_prefix(template,source_actions):
    classified=roles(template,template.source_contract.get('source_goal',''))
    boundary=next((i for i,action in enumerate(template.action_template) if action.startswith('focus on ') and
        any('goal_choice' in classified.get(p,[]) for p in re.findall(r'\{(\w+)\}',action))),None)
    if boundary is None or boundary==0:return None
    data=template.to_dict();data['action_template']=data['action_template'][:boundary]
    names=set(re.findall(r'\{(\w+)\}',' '.join(data['action_template'])))
    data['parameters']=[p for p in data['parameters'] if p in names]
    data['example_bindings']={p:v for p,v in data['example_bindings'].items() if p in names}
    data['template_id']='prefix_'+digest(data['action_template'])[:16]
    data['source_contract']=dict(data['source_contract'],preparation_only=True,full_skill_transfer_verified=False)
    fragment=ScienceSkillTemplate.from_dict(data);fragment.parameter_roles=roles(fragment,data['source_contract'].get('source_goal',''))
    assert source_valid(fragment,source_actions)
    return fragment

def public_references(view):
    refs=set()
    for action in view.get('valid_actions',[]):
        for prefix in ('look at ','look in ','focus on ','pick up ','open ','close ','go to '):
            if action.startswith(prefix):refs.add(action[len(prefix):].lower());break
    return refs

def condition_checks(template,view,bindings=None):
    text=template.applicability.strip();goal=view.get('goal','').lower();look=view.get('look','').lower();checks=[]
    bindings=bindings if isinstance(bindings,dict) else {};facts=public_facts(view)
    def add(name,value,evidence):checks.append({'condition':name,'value':value,'evidence':evidence})
    # Fully covered small contract, frozen from the existing compiler output.
    # The wood-block requirement is retained even after parameter lifting.
    plane_condition=re.fullmatch(r'([A-Za-z ]+) with a wood block and two inclined planes of different surface materials; goal is to compare friction and focus on the (lowest|highest)-friction plane\.',text)
    if plane_condition:
        location=facts['location'];expected_room=plane_condition.group(1).lower();add('required_room',location==expected_room if location else 'UNKNOWN',{'observed':location,'required':expected_room})
        add('wood_block_visible',True if re.search(r'\bwood block\b',look) else False if re.search(r'\ba brick\b',look) else 'UNKNOWN','current look')
        planes={x for x in public_references(view) if x.startswith('inclined plane with a ')}
        add('two_named_planes',len(planes)==2,sorted(planes))
        expected='least' if plane_condition.group(2)=='lowest' else 'most';opposite='most' if expected=='least' else 'least'
        add('goal_extremum_matches_condition',True if expected+' friction' in goal else False if opposite+' friction' in goal else 'UNKNOWN','literal current goal')
    elif text=='Agent is in a room with a portable non-living object and a closed door leading to the room containing the target container.':
        obj=bindings.get('object');room=bindings.get('room');container=bindings.get('container')
        add('portable_current_object',('pick up '+obj) in view.get('valid_actions',[]) if obj else 'UNKNOWN','public valid action, not a task-correctness oracle')
        add('object_is_non_living','UNKNOWN','Generic object name/portability does not prove biological category; no answer ontology supplied')
        add('closed_door_to_destination',facts['doors'][room]=='closed' if room in facts['doors'] else 'UNKNOWN','explicit current door description')
        add('destination_named_in_goal',bool(container and room and container.lower() in goal and room.lower() in goal),'literal destination names only')
    elif text=='Agent starts in an indoor room with a closed door leading toward the target location; candidate animals are present in the destination room and can be inspected and focused on.':
        location=facts['location'];room=bindings.get('room');animal=bindings.get('animal')
        add('not_already_outside',location!='outside' if location else 'UNKNOWN',location)
        add('closed_door_to_target',facts['doors'][room]=='closed' if room in facts['doors'] else 'UNKNOWN','explicit current door description')
        add('animal_visible_and_focusable',('focus on '+animal) in view.get('valid_actions',[]) if animal else 'UNKNOWN','explicit current action referent')
        add('animal_category_and_destination','UNKNOWN','Current visibility alone does not establish category, destination-room content or longevity ranking')
    else:
        add('raw_applicability_verified','UNKNOWN','Missing condition' if not text else 'Unsupported natural-language clauses retained verbatim')
    return checks

def conditional_bind(template,view,bindings):
    checks=condition_checks(template,view,bindings);issues=[];refs=public_references(view);goal=view.get('goal','').lower()
    if not isinstance(bindings,dict):bindings={}
    for param in template.parameters:
        value=bindings.get(param)
        if not isinstance(value,str) or not value:issues.append('MISSING_PARAMETER:'+param);continue
        # Goal naming is explicit evidence for a destination, not proof of a
        # conditional answer or unseen experimental property.
        if value.lower() not in refs and value.lower() not in goal:issues.append('NO_CURRENT_PUBLIC_REFERENT:'+param)
    for param,literal in template.source_contract.get('lifted_literal_constraints',{}).items():
        if bindings.get(param)!=literal:
            # Lifting syntax is not a proof that every action-valid entity has
            # the source object's experimental role or satisfies its condition.
            issues.append('LIFTED_OBJECT_ROLE_NOT_PROVEN:'+param)
    parameter_roles=template.parameter_roles or roles(template,template.source_contract.get('source_goal',goal))
    selectors=[p for p,r in parameter_roles.items() if 'goal_choice' in r]
    if selectors:
        # No certified comparison/measurement interpreter is provided here.
        # Seeing two planes or boxes does not identify the correct target.
        issues.extend('TARGET_SELECTION_UNPROVEN:'+p for p in selectors)
    try:
        actions=template.instantiate(bindings)
        if actions and actions[0] not in view.get('valid_actions',[]):issues.append('FIRST_ACTION_NOT_CURRENTLY_VALID')
    except (KeyError,TypeError):issues.append('INSTANTIATION_FAILED')
    if any(c['value'] is False for c in checks):status='REJECT_CONDITION_FALSE'
    elif issues or any(c['value']=='UNKNOWN' for c in checks):status='ABSTAIN_INSUFFICIENT_EVIDENCE'
    else:status='ALLOW'
    return {'accepted':status=='ALLOW','status':status,'conditions':checks,'issues':issues,
            'parameter_roles':parameter_roles,'raw_applicability':template.applicability,
            'safety_policy':'Existing source subsequence validation and every-step valid-action guard unchanged',
            'scope':'This bounded verifier may abstain because of parser coverage; abstention is not proof of non-transferability.'}
