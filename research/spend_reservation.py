"""Explicit conservative admission holds; never substitute estimates for provider usage."""
import json
from pathlib import Path
from research.artifacts import digest,file_digest
from research.jsonl_ledger import read_jsonl
from research.model_gateway import ModelGateway,BudgetExceeded,invocation_fingerprint


def load_reserves(directory,requests=None,calls=None):
    directory=Path(directory);path=directory/'admission_reserves.json'
    if not path.exists():return {}
    if (directory/'protocol.json').exists():
        protocol=json.loads((directory/'protocol.json').read_text(encoding='utf-8'))
        expected=protocol.get('admission_reserves_sha256')
        if expected is not None and file_digest(path)!=expected:raise ValueError('Reservation registry differs from frozen protocol')
    registry=json.loads(path.read_text(encoding='utf-8'))
    if registry.get('schema_version')!=1 or registry.get('mode')!='conservative_reservation_not_actual_usage' or not registry.get('authorization'):
        raise ValueError('Invalid explicit admission reservation registry')
    requests=read_jsonl(directory/'requests.jsonl') if requests is None else requests
    calls=read_jsonl(directory/'calls.jsonl') if calls is None else calls
    req={r['id']:r for r in requests};responses={r['id']:r for r in calls}
    errors={r['id'] for r in read_jsonl(directory/'invocation_errors.jsonl')}
    result={}
    for entry in registry.get('entries',[]):
        identity=entry['id'];request=req.get(identity);call=responses.get(identity);hold=entry.get('reserved_tokens')
        if not request or not call or identity in result or identity in errors:raise ValueError('Reservation has no eligible unique transport failure')
        if call.get('status')!='unknown' or call.get('usage') is not None or call.get('error_type')!='FrameworkError' or call.get('output')!='':
            raise ValueError('Only unreconciled pre-response FrameworkError is eligible')
        if digest(request)!=entry.get('request_sha256') or digest(call)!=entry.get('call_sha256'):
            raise ValueError('Reservation source identity changed')
        if type(hold) is not int or hold<max(10000,request.get('reserved_tokens',0)):
            raise ValueError('Reservation cannot reduce the conservative hold')
        result[identity]=hold
    return result


class ReservedSpendGateway(ModelGateway):
    """Opt-in explicit holds affect admission only; new unknown attempts still halt."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.reserves=load_reserves(self.directory,self.requests,self.calls)
        self.registry_hash=digest(self.reserves)

    def totals(self):
        totals=super().totals();reserves=load_reserves(self.directory,self.requests,self.calls)
        if hasattr(self,'registry_hash') and digest(reserves)!=self.registry_hash:
            raise ValueError('Admission reservations changed during execution')
        totals['unresolved_usage_ids']=list(totals['unknown_spend_ids'])
        totals['unknown_spend_ids']=[i for i in totals['unknown_spend_ids'] if i not in reserves]
        totals['reserved_unknown_tokens']=sum(reserves.values())
        totals['admission_total_tokens']=totals['known_api_tokens']+totals['reserved_unknown_tokens']
        return totals

    async def call(self,messages,tag,max_tokens=256,invoke=None):
        fingerprint=invocation_fingerprint(messages,tag,max_tokens,self.config['model'],self.config['provider'],digest(self.config['api_base']))
        cached=any(c.get('fingerprint')==fingerprint and c.get('status')=='ok' for c in self.calls)
        if not cached:
            reservation=2*self.count_tokens(json.dumps(messages,ensure_ascii=False))+512+max_tokens
            if self.totals()['admission_total_tokens']+reservation>self.max_total_tokens:
                raise BudgetExceeded('Known usage plus explicit unresolved-spend holds exceed admission cap')
        return await super().call(messages,tag,max_tokens,invoke)
