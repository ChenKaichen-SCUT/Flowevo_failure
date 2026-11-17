"""Regression checks for evidence boundaries, not new task-solving tests."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/'artifacts/success_audit'/name).read_text(encoding='utf-8'))

def test_source_review_freezes_before_compiler_join():
    manifest=read('source_manifest.json');labels=read('source_adjudicated.json')
    assert {r['job_id'] for r in labels}=={r['job_id'] for r in manifest['packets']}
    primary=[r for r in read('success_inventory.json') if r['scope']=='PRIMARY_TRAIN_DEV']
    assert len(primary)==len({r['unit'] for r in primary})==31
    assert {r['job_id'] for r in primary}==set(manifest['primary_representatives'].values())
    assert all('test' not in r['scope'].lower() for r in manifest['packets'])

def test_temperature_rule_is_not_reported_as_lost_from_all_layers():
    c=next(c for c in read('compilation_chain.json') if c['task']=='use-thermometer')
    rule=c['historical_exemplar']['rules'][2]
    assert 'above 0.0' in rule and 'blue box' in rule and 'below 0.0' in rule and 'orange box' in rule
    assert c['raw_rules_equal_historical_L2'] and 17 not in c['exact_source_alignment_1based']

def test_current_temperature_never_certifies_melting_point():
    r=next(r for r in read('source_adjudicated.json') if r['job_id']=='discovery-v2.F.3fbe681bf784f2d76d21')
    assert r['measurement_evidence_steps']==[5] and not r['decision_supported']
    assert not r['observed_decision_dependency']

def test_historical_missing_records_are_not_relabelled_as_historical_passes():
    absent=[c for c in read('compilation_chain.json') if not c['historical_compilation_file_present']]
    assert len(absent)==2 and all(c['historical_template'] is None and c['historical_rejection'] is None for c in absent)

def test_all_transfer_cases_preserve_score_blind_boundary():
    r=read('transfer_checks.json');assert not r['target_score_used'] and r['new_model_calls']==0 and r['new_JVM_actions']==0
    assert all(c['split'] in ('train','dev') and not c['full_transfer_demonstrated'] for c in r['cases'])
    p=read('transfer_plan.json')
    assert all(not {'score','reward','done','gold'}.intersection(c['view']) for c in p['cases'])
    temperature=[c for c in r['cases'] if c['kind']=='SYNTHETIC_MEASUREMENT_SIGN_CHANGE']
    assert len(temperature)==2 and all(c['synthetic'] for c in temperature)
    assert temperature[0]['instantiated_actions']==temperature[1]['instantiated_actions']

def test_input_completeness_and_rule_retention_have_separate_scopes():
    cs=read('compilation_chain.json')
    assert all(c['compiler_input_equal_to_all_public_steps'] for c in cs)
    assert all(not c['source_reason_sent_to_compiler'] for c in cs)
    assert all(c['raw_rules_equal_historical_L2'] for c in cs if c['historical_exemplar'])
    assert all(c['A2_applicability_preserved'] for c in cs if c['current_cached_template'])
