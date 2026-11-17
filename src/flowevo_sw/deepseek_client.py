import json,httpx

class DeliveryError(RuntimeError):pass
class ParseError(RuntimeError):pass

class DeepSeekClient:
    def __init__(self,job_id,stage='action',endpoint='http://127.0.0.1:8765',meta=None):
        self.job_id=job_id;self.stage=stage;self.counter=0;self.endpoint=endpoint
        self.http=httpx.Client(timeout=360,trust_env=False);self.meta=meta or {};self.records=[]
    def call(self,instructions,input_text,stage=None,learning=False):
        stage=stage or self.stage;self.counter+=1;rid=f'{self.job_id}.{stage}.{self.counter:04d}'
        response=self.http.post(self.endpoint+'/request',json={'request_id':rid,'messages':[{'role':'system','content':instructions},{'role':'user','content':input_text}], 'max_tokens':8192 if learning else 2048,'meta':dict(self.meta,job_id=self.job_id,stage=stage)})
        if response.status_code!=200:raise DeliveryError(response.text[:240])
        body=response.json();self.records.append({'request_id':rid,'usage':body.get('usage',{}),'model':body.get('model')})
        choice=body['choices'][0]
        if choice.get('finish_reason')!='stop':
            self.parsed(rid,'DELIVERY_TRUNCATED');raise DeliveryError('DELIVERY_TRUNCATED')
        return choice['message'].get('content',''),rid,body.get('usage',{})
    def parsed(self,rid,status):
        self.http.post(self.endpoint+'/parsed',json={'request_id':rid,'status':status})
    def json(self,instructions,data,stage=None,learning=False):
        raw,rid,usage=self.call(instructions+' Return one JSON object, no markdown.',json.dumps(data,ensure_ascii=False),stage,learning)
        try:
            obj=json.loads(raw)
            if not isinstance(obj,dict):raise ValueError()
        except (ValueError,TypeError):
            self.parsed(rid,'ACTION_PARSE_ERROR');raise ParseError('ACTION_PARSE_ERROR')
        self.parsed(rid,'VALID_JSON');return obj,raw,rid,usage
