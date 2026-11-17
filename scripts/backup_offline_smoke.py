"""Verify restored imports, ledger and a JVM reset; never solve or call a provider."""
import argparse, hashlib, json, os, sqlite3, subprocess, sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--restored',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    root=Path(a.restored).resolve();project=root/'root/flowevo-scienceworld';latest=root/'root/flowevo-success-trace/output'
    assert os.environ.get('FLOWEVO_OFFLINE_ONLY')=='1'
    interfaces=sorted(r['ifname'] for r in json.loads(subprocess.check_output(['ip','-json','link','show'])))
    assert interfaces==['lo'],'Run under unshare -n with loopback only'
    import flowevo_sw,alfworld_,scienceworld,py4j,numpy
    modules={m.__name__:str(Path(m.__file__).resolve()) for m in (flowevo_sw,alfworld_,scienceworld,py4j,numpy)}
    assert all(Path(f).is_relative_to(root) for f in modules.values()),modules
    with sqlite3.connect((project/'runs-private/ledger.sqlite').as_uri()+'?mode=ro',uri=True) as c:
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        counts=list(c.execute('SELECT count(*),sum(cost) FROM requests').fetchone())
    assert counts[0]==8941 and abs(counts[1]-12.375240828)<1e-8
    from flowevo_sw.adapter import ScienceWorldAdapter
    env=ScienceWorldAdapter()
    try:
        view=env.reset('melt',4)
        assert view['goal'] and view['look'] and view['valid_actions']
        look_hash=hashlib.sha256(view['look'].encode()).hexdigest()
    finally:env.close()
    with sqlite3.connect((project/'runs-private/ledger.sqlite').as_uri()+'?mode=ro',uri=True) as c:
        assert counts==list(c.execute('SELECT count(*),sum(cost) FROM requests').fetchone())
    result={'status':'PASSED','all_imports_from_restored_snapshot':True,'modules':modules,
      'ledger_requests':counts[0],'ledger_historical_cost':counts[1],'new_model_calls':0,
      'JVM_reset_task':'melt:4 (historical TRAIN)','JVM_reset_passed':True,'new_environment_actions':0,
      'initial_look_sha256':look_hash,'network_interfaces':interfaces,'python':sys.version.split()[0]}
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
