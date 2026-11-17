import copy,json,pytest
from flowevo_sw.credit_accounting import ScienceSkillLibrary
from flowevo_sw.skill_contracts import ScienceSkillTemplate
from flowevo_sw.action_consistency import inspect_response
from flowevo_sw.conditional_binding import source_valid,repair_source_parameters,conditional_bind,preparation_prefix,lift_literal_experiment_object

def test_offline_guard_stops_client_creation_and_existing_client_calls(monkeypatch):
    from flowevo_sw.deepseek_client import DeepSeekClient,DeliveryError
    monkeypatch.setenv('FLOWEVO_OFFLINE_ONLY','1')
    with pytest.raises(DeliveryError,match='OFFLINE_ONLY'):DeepSeekClient('must-not-connect')
    uninitialized=DeepSeekClient.__new__(DeepSeekClient)
    with pytest.raises(DeliveryError,match='OFFLINE_ONLY'):uninitialized.call('x','y')

def record(sources,completed=False,episode_success=True):
    return {'trace':{'task_type':'fixture','success':episode_success,'direct_use_count':1,'strategy_holdout':False},
      'retrieved':{'template':{'template_id':'t'},'exemplar':{'exemplar_id':'e'},'insight':None},
      'steps':[{'source':source,'host_outcome':{'success':completed and i==0}} for i,source in enumerate(sources)]}
def library():
    lib=ScienceSkillLibrary();lib.add_template(ScienceSkillTemplate('t','fixture',['look around'],[]));return lib

def test_no_execution_is_exposure_only():
    lib=library();event=lib.record_episode_credits(record(['skill_guided']))
    assert not event['direct_credit_updated']
    assert lib.to_dict()['template_use_count']['t']==0
    assert lib.credit_ledger['retrieval']['template:t']=={'retrieved':1,'retrieved_only':1}
    assert lib.credit_ledger['guidance']['exemplar:e']['episodes_exposed']==1

def test_fallback_success_never_becomes_direct_success():
    lib=library();lib.record_episode_credits(record(['direct_skill','skill_guided'],False,True))
    assert lib.to_dict()['template_utility']['t']==0
    assert lib.credit_ledger['direct']['t']['incomplete_direct_attempts']==1
    assert lib.credit_ledger['guidance']['exemplar:e']['mixed_direct_prefix_episodes']==1

def test_direct_completion_does_not_credit_uninjected_guidance():
    lib=library();lib.record_episode_credits(record(['direct_skill'],True,True))
    assert lib.to_dict()['template_success_count']['t']==1
    assert not lib.credit_ledger['guidance']

def test_zero_action_direct_entry_is_not_a_use():
    lib=library();lib.record_episode_credits(record([]))
    assert lib.to_dict()['template_use_count']['t']==0

def test_l2_l3_coexposure_counted_without_double_guided_episode():
    lib=library();r=record(['skill_guided']);r['retrieved']['insight']={'task_type':'fixture','common_pitfalls':['Public issue'],'sample_count':3}
    lib.record_episode_credits(r)
    assert set(lib.credit_ledger['guidance'])=={'exemplar:e','insight:fixture'}
    assert lib.to_dict()['contrastive_stats']['fixture']['guided_total']==1
    assert lib.credit_ledger['guidance']['insight:fixture']['coexposed_guidance_episodes']==1

def test_inactivity_starts_at_admission_without_fabricated_usage():
    lib=ScienceSkillLibrary()
    for _ in range(80):lib.advance_episode()
    lib.add_template(ScienceSkillTemplate('t','fixture',['look around'],[]));lib.periodic_audit()
    assert lib.retrieve('fixture')['template'] is not None
    assert 't' not in lib.to_dict()['template_last_used']
    for _ in range(51):lib.advance_episode()
    assert lib.periodic_audit()['suppressed_inactive']==[('t',51.0)]

def test_native_direct_failure_suppression_retained():
    lib=library()
    for _ in range(3):lib.record_episode_credits(record(['direct_skill'],False,False))
    assert lib.retrieve('fixture')['template'] is None

def test_metadata_roundtrip_and_legacy_loading():
    lib=ScienceSkillLibrary();template=ScienceSkillTemplate('t','fixture',['look around'],[],applicability='Retain verbatim',parameter_roles={'x':['instrument']},source_contract={'source_goal':'public goal'})
    lib.add_template(template);restored=ScienceSkillLibrary.from_dict(lib.to_dict())
    assert restored.retrieve('fixture')['template'].to_dict()==template.to_dict()
    assert restored.template_admitted_at==lib.template_admitted_at
    assert ScienceSkillLibrary.from_dict({}).retrieve('fixture')['template'] is None

def test_file_reload_preserves_conditions_and_credit(tmp_path):
    lib=library();lib._templates['t'].applicability='Retain verbatim'
    lib._templates['t'].parameter_roles={'object':['experiment_subject']}
    lib.record_episode_credits(record(['direct_skill'],False,False))
    path=tmp_path/'library.json';lib.save(path)
    restored=ScienceSkillLibrary();restored.load(path)
    assert restored.to_dict()==lib.to_dict()
    assert restored.retrieve('fixture')['template'].applicability=='Retain verbatim'
    restored.load(tmp_path/'missing.json')
    assert restored.to_dict()==lib.to_dict()

def test_literal_lifting_never_mutates_original_or_serialized_snapshot():
    source=['look at glass plane','connect block to glass plane','focus on glass plane']
    template=ScienceSkillTemplate('t','fixture',['look at {plane}','connect block to {plane}','focus on {plane}'],['plane'],{'plane':'glass plane'},applicability='Original condition')
    before=template.to_dict();lifted=lift_literal_experiment_object(template,source)
    assert template.to_dict()==before and source_valid(template,source) and source_valid(lifted,source)
    data=template.to_dict();data['parameters'].append('bad');data['example_bindings']['plane']='wrong'
    assert template.to_dict()==before

def test_unique_parameter_split_keeps_exact_source_validation():
    actions=['open door to hallway','go to hallway','open door to kitchen','go to kitchen']
    generated={'action_template':['open door to {room}','go to {room}','open door to {room}','go to {room}'],'applicability':'Original condition'}
    repaired,diagnostic=repair_source_parameters(generated,actions,'fixture','trace','Find object')
    assert diagnostic['status']=='SOURCE_VALID_CANDIDATE'
    assert repaired.example_bindings=={'room_1':'hallway','room_2':'kitchen'}
    assert source_valid(repaired,actions) and not source_valid(repaired,actions[:-1])
    assert repaired.applicability=='Original condition'

def test_ambiguous_source_alignment_is_not_silently_repaired():
    repaired,status=repair_source_parameters({'action_template':['look at {object}']},['look at cup','look at picture'],'fixture','trace','Find object')
    assert repaired is None and status['status']=='AMBIGUOUS_ALIGNMENT'

def view():return {'goal':'If above 50 degrees, focus on the red box. If below 50, focus on the green box.',
    'look':'This room is called the hallway. A door to the kitchen (that is closed)',
    'inventory':'','observation':'','valid_actions':['focus on red box','focus on green box','open door to kitchen','go to kitchen']}
def check(action,reason,v=None):return inspect_response(json.dumps({'action':action,'reason':reason}),v or view())

def test_explicit_correction_conflict_only_alerts():
    result=check('focus on red box','Correct action: focus on green box.')
    assert result['reason_action_relation']=='EXPLICIT_CONFLICT'
    assert result['parsed_action']=='focus on red box' and result['policy']=='REPORT_ONLY'
    assert 'replacement_action' not in result

def test_quoted_conditional_goal_is_not_reason_action_conflict():
    result=check('focus on red box','If below 50, focus on green box; if above 50, focus on red box.')
    assert not any(w['category']=='REASON_ACTION_CONFLICT' for w in result['warnings'])

def test_pronoun_and_underspecified_description_are_not_conflicts():
    result=check('open door to kitchen','I need to open its closed door before entering to search.')
    assert not result['warnings']

def test_public_door_wording_variant():
    result=check('open door to kitchen','Next, open the closed kitchen door so I can enter.')
    assert result['reason_action_relation']=='NORMAL_WORDING_VARIANT' and not result['warnings']

def test_route_subgoal_and_generic_animal_are_not_definite_conflicts():
    v=view();v['goal']='Find an animal and move it to the bathroom.';v['valid_actions']+=['pick up bee 3','go to hallway']
    assert not check('pick up bee 3','I need to pick up an animal, then carry it.',v)['warnings']
    assert not check('go to hallway','I need to travel to the bathroom to place it there.',v)['warnings']

def test_focus_required_by_goal_is_not_banned():
    v=view();v['goal']='First, focus on the thermometer. Next, focus on the substance.'
    result=check('focus on thermometer','First identify the required thermometer.',v)
    assert not result['warnings'] and result['focus_role']=='EXPLICIT_GOAL_FOCUS_CANDIDATE'

def test_wrong_object_class_and_inspection_are_separate():
    v=view();v['goal']='First, focus on the red light bulb.'
    result=check('focus on red paint in cup','Focus on this to inspect its properties.',v)
    assert {'TARGET_OBJECT_MISMATCH','FOCUS_AS_INSPECTION'}<={w['category'] for w in result['warnings']}

def test_checker_does_not_consult_hidden_outcomes():
    original=view();private=dict(original,score=100,gold='green box',done=True)
    assert check('focus on red box','Correct action: focus on green box.',original)==check('focus on red box','Correct action: focus on green box.',private)

def plane_template():
    return ScienceSkillTemplate('plane','fixture',['look at {plane}','focus on {plane}'],['plane'],{'plane':'inclined plane with a glass surface'},
      applicability='Workshop with a wood block and two inclined planes of different surface materials; goal is to compare friction and focus on the lowest-friction plane.',
      source_contract={'source_goal':'Find the plane with least friction.'})
def plane_view():
    return {'goal':'Find the plane with the least friction.','look':'This room is called the workshop. A wood block.',
      'valid_actions':['look at inclined plane with a glass surface','look at inclined plane with a brass surface','focus on inclined plane with a glass surface']}

def test_seeing_candidates_does_not_prove_answer():
    verdict=conditional_bind(plane_template(),plane_view(),{'plane':'inclined plane with a glass surface'})
    assert not verdict['accepted'] and 'TARGET_SELECTION_UNPROVEN:plane' in verdict['issues']

def test_preparation_can_bind_without_committing_to_answer():
    template=plane_template();prefix=preparation_prefix(template,template.instantiate(template.example_bindings))
    assert conditional_bind(prefix,plane_view(),{'plane':'inclined plane with a glass surface'})['accepted']
    assert prefix.source_contract['preparation_only'] and not any(a.startswith('focus on') for a in prefix.action_template)

def test_condition_false_and_unknown_remain_non_allowing():
    template=plane_template();v=plane_view();v['look']='This room is called the workshop. A brick.'
    assert conditional_bind(template,v,template.example_bindings)['status']=='REJECT_CONDITION_FALSE'
    template.applicability='Some unparsed condition.'
    assert not conditional_bind(template,plane_view(),template.example_bindings)['accepted']
