"""Single localhost coordinator: one asynchronous semaphore and HTTP connection pool."""
import argparse,asyncio,os,re,time,json
from pathlib import Path
import httpx
from aiohttp import web
from .budget_ledger import BudgetLedger,BudgetExceeded,UnknownRequest
from .checkpointing import atomic_json,digest,read_json,canonical

async def build_app(args):
    key=Path(args.api_key_file).read_text().strip()
    if not re.fullmatch(r'sk-[A-Za-z0-9_-]+',key):raise ValueError('Invalid single-line DeepSeek key format')
    os.chmod(args.api_key_file,0o600)
    root=Path(args.private_dir);root.mkdir(parents=True,exist_ok=True)
    ledger=BudgetLedger(root/'ledger.sqlite',args.budget)
    semaphore=asyncio.Semaphore(args.concurrency)
    http=httpx.AsyncClient(timeout=httpx.Timeout(300,connect=20),limits=httpx.Limits(max_connections=args.concurrency,max_keepalive_connections=args.concurrency),trust_env=False)
    async def health(req):return web.json_response({'concurrency':args.concurrency,'budget':args.budget,'ledger':ledger.summary()})
    async def call(req):
        d=await req.json();rid=d['request_id']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+',rid):raise web.HTTPBadRequest()
        max_tokens=int(d.get('max_tokens',2048))
        if max_tokens not in (2048,8192):raise web.HTTPBadRequest(text='unfrozen output cap')
        payload={'model':'deepseek-flash','messages':d['messages'],'temperature':0,'max_tokens':max_tokens,'thinking':{'type':'disabled'}}
        wire=canonical(payload)
        if key in wire:raise web.HTTPBadRequest(text='Secret detected in payload')
        reservation=((len(wire.encode())+512)*.30+max_tokens*1.20)/1e6
        queued=time.time()
        async with semaphore:
            try:existing=ledger.reserve(rid,digest(payload),reservation,d.get('meta',{}))
            except BudgetExceeded as exc:return web.json_response({'error':'BUDGET_EXHAUSTED'},status=402)
            except (UnknownRequest,ValueError) as exc:return web.json_response({'error':str(exc)},status=409)
            if existing:return web.json_response(read_json(existing['response_path'])['response'])
            path=root/'requests'/(rid+'.json')
            atomic_json(root/'requests'/(rid+'.request.json'),{'request_id':rid,'payload':payload,'meta':d.get('meta',{}),'wire_hash':digest(payload),'reserved_cost':reservation,'queue_seconds':time.time()-queued,'endpoint':'https://api.deepseek.com/chat/completions'})
            started=time.time()
            try:
                response=await http.post('https://api.deepseek.com/chat/completions',json=payload,headers={'Authorization':'Bearer '+key})
                if response.status_code!=200:
                    atomic_json(path,{'status':response.status_code,'body':response.text.replace(key,'[REDACTED]'),'latency':time.time()-started})
                    if 400<=response.status_code<500:ledger.rejected(rid)
                    else:ledger.unknown(rid)
                    return web.json_response({'error':'PROVIDER_HTTP_'+str(response.status_code)},status=502)
                body=response.json()
                atomic_json(path,{'request_id':rid,'response':body,'latency':time.time()-started})
                ledger.saved(rid,path);ledger.settle(rid,body,path)
                return web.json_response(body)
            except Exception as exc:
                ledger.unknown(rid)
                return web.json_response({'error':'UNKNOWN_'+type(exc).__name__},status=502)
    async def parsed(req):
        d=await req.json();ledger.parsed(d['request_id'],d['status']);return web.json_response({'ok':True})
    app=web.Application(client_max_size=4*1024**2)
    app.router.add_get('/health',health);app.router.add_post('/request',call);app.router.add_post('/parsed',parsed)
    async def cleanup(app):await http.aclose()
    app.on_cleanup.append(cleanup)
    return app

def main():
    p=argparse.ArgumentParser();p.add_argument('--api-key-file',required=True);p.add_argument('--private-dir',required=True);p.add_argument('--budget',type=float,default=100);p.add_argument('--concurrency',type=int,default=8);p.add_argument('--port',type=int,default=8765)
    args=p.parse_args();web.run_app(build_app(args),host='127.0.0.1',port=args.port,print=None,access_log=None)
if __name__=='__main__':main()
