from pathlib import Path
import yaml

def load_config(root):
    c=yaml.safe_load((Path(root)/'output/configs/experiment_plan.yaml').read_text())
    p=c['provider'];s=c['scienceworld'];f=c['flowevo']
    assert p['vendor']=='deepseek' and p['model']=='deepseek-flash' and p['base_url']=='https://api.deepseek.com'
    assert p['thinking']=='disabled' and p['temperature']==0 and not p['allow_other_model_providers'] and not p['sdk_automatic_retries']
    assert s['simplifications']=='' and s['episode_limit']==100
    assert not any(s[k] for k in ('generate_gold_path','solver_gold_access','solver_private_world_state_access','solver_hidden_goal_progress_access','solver_numeric_score_visibility'))
    assert all(f[k] for k in ('success_compilation','success_library_admission','retrieval','direct_skill_execution','skill_conditioned_generation','native_dynamic_fallback','governance','all_actions_through_gateway'))
    assert not f['gold_in_retry_prompt'] and not f['hidden_correctness_driven_retry']
    assert c['budget']['max_api_cost_usd']==100 and c['constraints']['max_active_rules']<=3
    return c
