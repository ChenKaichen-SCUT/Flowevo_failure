"""One transaction reserves cost before a network send; unresolved sends retain cost."""
import sqlite3,time,json

class BudgetExceeded(RuntimeError):pass
class UnknownRequest(RuntimeError):pass

class BudgetLedger:
    def __init__(self,path,cap=100):
        self.path=str(path);self.cap=cap
        with self.db() as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, wire_hash TEXT, state TEXT, reserved REAL, cost REAL DEFAULT 0, started REAL, finished REAL, meta TEXT, usage TEXT, response_path TEXT, parse_status TEXT, provider_id TEXT, model TEXT, finish_reason TEXT)')
    def db(self):
        c=sqlite3.connect(self.path,timeout=30);c.row_factory=sqlite3.Row;return c
    def reserve(self,rid,wire_hash,cost,meta):
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone()
            if row:
                if row['wire_hash']!=wire_hash:raise ValueError('request_id payload conflict')
                if row['state']=='SETTLED':return dict(row)
                raise UnknownRequest('Existing unresolved request: '+rid)
            used=c.execute("SELECT COALESCE(SUM(cost+CASE WHEN state IN ('STARTED','UNKNOWN','RESPONSE_SAVED') THEN reserved ELSE 0 END),0) FROM requests").fetchone()[0]
            if used+cost>self.cap:raise BudgetExceeded('Global reserved budget exhausted')
            c.execute('INSERT INTO requests(id,wire_hash,state,reserved,started,meta) VALUES(?,?,?,?,?,?)',(rid,wire_hash,'STARTED',cost,time.time(),json.dumps(meta)))
        return None
    def saved(self,rid,path):
        with self.db() as c:c.execute("UPDATE requests SET state='RESPONSE_SAVED',response_path=? WHERE id=?",(str(path),rid))
    def settle(self,rid,response,path):
        u=response.get('usage',{})
        if 'prompt_tokens' not in u or 'completion_tokens' not in u:
            self.unknown(rid);raise UnknownRequest('Response lacks billable usage')
        hit=u.get('prompt_cache_hit_tokens',0);miss=u.get('prompt_cache_miss_tokens',u['prompt_tokens']-hit)
        cost=(hit*.006+miss*.30+u['completion_tokens']*1.20)/1e6
        choice=response.get('choices',[{}])[0]
        with self.db() as c:
            c.execute("UPDATE requests SET state='SETTLED',cost=?,finished=?,usage=?,response_path=?,provider_id=?,model=?,finish_reason=? WHERE id=?",(cost,time.time(),json.dumps(u),str(path),response.get('id'),response.get('model'),choice.get('finish_reason'),rid))
    def rejected(self,rid):
        with self.db() as c:c.execute("UPDATE requests SET state='REJECTED',finished=? WHERE id=?",(time.time(),rid))
    def unknown(self,rid):
        with self.db() as c:c.execute("UPDATE requests SET state='UNKNOWN',finished=? WHERE id=?",(time.time(),rid))
    def parsed(self,rid,status):
        with self.db() as c:c.execute('UPDATE requests SET parse_status=? WHERE id=?',(status,rid))
    def summary(self):
        with self.db() as c:
            return [dict(x) for x in c.execute('SELECT state,COUNT(*) n,SUM(cost) estimated_peak_usd,SUM(reserved) reserved_original FROM requests GROUP BY state')]
