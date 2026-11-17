"""Credential-free helpers shared by the engineering falsification scripts."""
import ast,copy,csv,hashlib,json,subprocess
from pathlib import Path
from alfworld_.schemas import AlfWorldTrace,AlfWorldAction
from flowevo_sw.skill_contracts import ScienceSkillTemplate

FROZEN='a0f6e0816c23a4abcb646a5fb018e786c2a6be95'
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def csv_write(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:path.write_text('',encoding='utf-8');return
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
def publisher(repo,legacy=False):
    source=subprocess.check_output(['git','show',FROZEN+':src/flowevo_sw/batch_runner.py'],cwd=repo) if legacy else (repo/'src/flowevo_sw/batch_runner.py').read_bytes()
    nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in ('restore_trace','publish_batch')]
    assert len(nodes)==2
    namespace={'copy':copy,'digest':digest,'AlfWorldTrace':AlfWorldTrace,'AlfWorldAction':AlfWorldAction,'ScienceSkillTemplate':ScienceSkillTemplate}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual publication function bodies>','exec'),namespace)
    return namespace['publish_batch']

def records(inp):
    return {d['job_id']:d for f in sorted((inp/'episodes').glob('*.json')) if '.prefix.' not in f.name for d in [read(f)]}
