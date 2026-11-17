import copy,json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import pytest
from flowevo_sw.budget_ledger import BudgetLedger,BudgetExceeded,UnknownRequest
from flowevo_sw.public_view import public_view,parse_action
from flowevo_sw.adapter import SolverFacade,ScienceWorldAdapter,Receipt
from flowevo_sw.deepseek_client import ParseError,DeliveryError
from flowevo_sw.action_gateway import ActionGateway,Veto
from flowevo_sw.invariant_runtime import check
from flowevo_sw.invariant_schema import validate_expr
from flowevo_sw.flowevo_adapter import ScienceExecutor,ScienceCompiler
from alfworld_.executor import AlfWorldExecutor
from alfworld_.schemas import AlfWorldSkillTemplate,AlfWorldTask
from alfworld_.skill_library import SkillLibrary

@pytest.mark.parametrize('name',['get_gold_action_sequence','getGoldActionSequence','getObjectTree','get_goal_progress','getGoalProgressStr','server','_gateway'])
def test_private_api_denied(name):
    with pytest.raises(PermissionError):getattr(SolverFacade({}),name)

def test_allowlist():
    v=public_view('normal feedback',{'score':100,'reward':1,'done':True,'gold':'SECRET','look':'room','inv':'bag','valid':['look around']})
    assert not any(k in v for k in ('score','reward','done','gold'))
    assert v['observation']=='normal feedback'

@pytest.mark.parametrize('raw',['','Act: look','{','{}','{"action":[]}','{"action":""}','{"action":"look\\nwait"}'])
def test_parse_no_fallback(raw):
    with pytest.raises(ParseError):parse_action(raw)

def test_illegal_and_ambiguous_actions_preserved():
    assert parse_action('{"action":"nonsense"}')=='nonsense'
    assert parse_action('{"action":"0"}')=='0'
    with pytest.raises(DeliveryError):parse_action('{"action":"look"}','length')

def test_done_not_success():
    e=ScienceWorldAdapter.__new__(ScienceWorldAdapter);e.info={'score':50,'moves':101};e.native=False;e.done=True;e.decisions=100;e.limit=100;e.highest=70
    assert not e.outcome()['success']
    e.native=True;assert not e.outcome()['success']
    e.info['score']=100;assert e.outcome()['success']

def test_concurrent_budget(tmp_path):
    l=BudgetLedger(tmp_path/'ledger',1)
    def reserve(i):
        try:l.reserve(str(i),str(i),.3,{});return True
        except BudgetExceeded:return False
    with ThreadPoolExecutor(max_workers=20) as p:assert sum(p.map(reserve,range(20)))==3

def test_settle_before_parse_and_recovery(tmp_path):
    l=BudgetLedger(tmp_path/'ledger',1);l.reserve('r','h',.1,{})
    resp={'usage':{'prompt_tokens':100,'completion_tokens':10},'choices':[{'finish_reason':'stop','message':{'content':'invalid JSON'}}]}
    l.saved('r','saved');l.settle('r',resp,'saved');l.parsed('r','ACTION_PARSE_ERROR')
    existing=l.reserve('r','h',.1,{})
    assert existing['cost']>0 and existing['parse_status']=='ACTION_PARSE_ERROR'
    l.reserve('u','h',.1,{});l.unknown('u')
    with pytest.raises(UnknownRequest):l.reserve('u','h',.1,{})

def test_isolated_snapshots_and_native_governance():
    template=AlfWorldSkillTemplate('t','test',['look'],[])
    original=SkillLibrary();snapshot=original.to_dict();a=SkillLibrary.from_dict(copy.deepcopy(snapshot));b=SkillLibrary.from_dict(copy.deepcopy(snapshot))
    a.add_template(template);assert b.retrieve('test')['template'] is None
    assert original.retrieve('test')['template'] is None
    for _ in range(3):a.record_template_usage('t',False)
    assert a.retrieve('test')['template'] is None
    assert a.to_dict()['template_status']['t']=='suppressed'

def rule():
    return dict(rule_id='test',version=1,source_evidence_ids=['fixture'],scope='fixture',public_state_requirements=[],trigger={'eq':['action','blocked']},protected_property='fixture',invalidation='none',exceptions=[],on_unknown='ABSTAIN',counterexamples=[],validation_status='TEST_ONLY')

class FakeAdapter:
    def __init__(self):self.done=False;self.decisions=0;self.view={'goal':'fixture','look':'fixture','inventory':'','observation':'','valid_actions':['blocked','look','finish']};self.executed=[]
    def context(self):return dict(self.view,history=[])
    def execute(self,action):
        self.executed.append(action);self.decisions+=1;self.done=action=='finish'
        self.view['observation']='observed '+action
        return Receipt(self.view['observation'],100 if self.done else 0,self.done,self.done,self.view['valid_actions'])
    def outcome(self):return {'success':self.done}

def test_gateway_disabled_identity_and_veto_no_steps():
    a,b=FakeAdapter(),FakeAdapter();ga=ActionGateway(a,arm='F');gb=ActionGateway(b,arm='F-I',rules=[])
    for action in ['look','finish']:assert ga.step(action)==gb.step(action)
    c=FakeAdapter();g=ActionGateway(c,arm='F-I',rules=[rule()])
    for replanned in [False,True]:
        with pytest.raises(Veto):g.step('blocked',replanned=replanned)
    assert c.decisions==0

def test_inherited_routing_direct_guided_fallback():
    assert ScienceExecutor.run is AlfWorldExecutor.run
    class Gen:
        last={'raw':'{"action":"finish"}','request_id':'fixture'}
        def step(self,*args,**kwargs):return SimpleNamespace(action='finish',prompt_tokens=1,completion_tokens=1)
    a=FakeAdapter();g=ActionGateway(a);ex=ScienceExecutor(g,Gen(),max_steps=100)
    t=AlfWorldSkillTemplate('t','test',['look'],[])
    from alfworld_.schemas import AlfWorldExemplar
    guide=AlfWorldExemplar('e','test','fixture',['Fixture instruction'])
    tr=ex.run(AlfWorldTask('x','test','fixture'),'',['look'],skill_bindings={},skill_library_result={'best_layer':1,'template':t,'exemplar':guide})
    assert tr.success and tr.fallback_triggered and tr.skill_seeded
    assert [s['source'] for s in g.steps]==['direct_skill','skill_guided']

def test_no_private_predicate():
    for field in ['score','reward','task_id','variation_id','gold','world_tree']:
        with pytest.raises(ValueError):validate_expr({'eq':[field,'x']})
    r=rule();r['trigger']={'contains':['last_feedback','closed']}
    assert check(r,{'history':[]},'look')['decision']=='ABSTAIN'

def test_current_public_state_and_object_binding():
    from flowevo_sw.shared_state import action_facts,public_facts
    c={'look':'This room is called the hallway. A door to the kitchen (that is closed)\nA door to the bedroom (that is open)'}
    assert action_facts(c,'go to kitchen')['target_door_state']=='closed'
    assert action_facts(c,'go to door to bedroom')['target_door_state']=='open'
    assert action_facts(c,'go to bathroom')['target_door_state'] is None
    c['look']='This room is called the kitchen.'
    assert action_facts(c,'go to kitchen')['target_door_state'] is None

def test_direct_veto_allows_only_one_replan():
    class Gen:
        last={'raw':'{"action":"blocked"}','request_id':'fixture'}
        def __init__(self):self.n=0
        def step(self,*args,**kwargs):self.n+=1;return SimpleNamespace(action='blocked',prompt_tokens=1,completion_tokens=1)
    a=FakeAdapter();g=ActionGateway(a,arm='F-I',rules=[rule()]);gen=Gen();ex=ScienceExecutor(g,gen,max_steps=100)
    template=AlfWorldSkillTemplate('t','test',['blocked'],[])
    tr=ex.run(AlfWorldTask('x','test','fixture'),'',['blocked'],skill_bindings={},skill_library_result={'best_layer':1,'template':template})
    assert gen.n==1 and a.decisions==0 and tr.failure_type=='PERSISTENT_CONSTRAINT_CONFLICT'
