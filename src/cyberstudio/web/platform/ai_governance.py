"""AI governance records, explicit release gates and source provenance. No model execution."""
from datetime import date
from pathlib import Path
import hashlib,json
from .ai_catalog import AI_MODULES

CONTEXT_KINDS={'ai_dataflow','ai_agent'}
BASE_REVIEWS={'business','vendor','security','privacy','contract','operations'}

def reference():
    return json.loads(Path(__file__).with_name('ai_reference.json').read_text(encoding='utf-8'))

def rows(db,org):
    from .store import fail
    records=[dict(r) for r in db.execute('SELECT * FROM pl_records WHERE organization_id=%s AND kind=ANY(%s) AND deleted_at IS NULL ORDER BY created_at,id LIMIT 5001',(org,list(AI_MODULES))).fetchall()]
    if len(records)>5000:fail('AI governance scope exceeds 5000 records; narrow the operating organization',409)
    return records

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()

def context_hash(case,records):
    context=[{'id':r['id'],'version':r['version'],'status':r['status']} for r in records if r['kind'] in CONTEXT_KINDS and r['data'].get('use_case_id')==case['id']]
    charter=next((r for r in records if r['id']==case['data'].get('charter_id')),None)
    authority={'id':charter['id'],'version':charter['version'],'status':charter['status']} if charter else case['data'].get('charter_id')
    return digest({'case':case['id'],'version':case['version'],'authority':authority,'context':sorted(context,key=lambda r:r['id'])})

def validate_record(db,org,kind,data):
    from .store import reference as related,fail
    today=date.today().isoformat()
    for key in ('business_owner','reviewer','response_owner'):
        if data.get(key) and not db.execute("SELECT 1 FROM web_users u WHERE username=%s AND enabled AND (role='owner' OR EXISTS(SELECT 1 FROM xp_memberships m WHERE m.username=u.username AND m.organization_id=%s))",(data[key],org)).fetchone():fail('Choose an enabled organization member for '+key)
    if kind=='ai_use_case':
        high=any(data.get(k)!='no' for k in ('phi','clinical','patient_facing'))
        if high and data['risk_tier'] in {'lower','moderate'}:fail('Sensitive, clinical, patient-facing or unknown exposure requires at least High pending review')
        if data['autonomy']=='consequential_actions' and data['risk_tier']!='critical':fail('Consequential autonomy requires the Critical / special-review pathway')
        if not data.get('review_on'):fail('Set the next governance review date')
    if kind in {'ai_decision','ai_exception'} and (not data.get('expires_on') or data['expires_on']<today):fail('Set an expiration date today or later')
    if kind.startswith('ai_') and data.get('use_case_id'):
        case=related(db,org,data['use_case_id'],'ai_use_case')
        data['calculated']={'context_hash':context_hash(case,rows(db,org)),'use_case_version':case['version']}
        if kind=='ai_decision':
            data['calculated']['readiness_hash']=readiness(db,org,case)['readiness_hash']
    return data

def readiness(db,org,case,records=None):
    from .store import require_verified_evidence
    from fastapi import HTTPException
    records=rows(db,org) if records is None else records
    linked=[r for r in records if r['data'].get('use_case_id')==case['id']]
    scope=context_hash(case,records);today=date.today().isoformat();blockers=[];required=set(BASE_REVIEWS)
    if case['data'].get('clinical')!='no' or case['data'].get('patient_facing')!='no':required.add('clinical')
    if case['data'].get('risk_tier')=='critical':required.add('special_authority')
    if case['status']=='closed':blockers.append('Use case is closed or retired')
    if case['data'].get('review_on','')<today:blockers.append('Governance review date is missing or overdue')
    if any(case['data'].get(k)=='unknown' for k in ('phi','clinical','patient_facing')):blockers.append('Resolve unknown sensitive-data, clinical and patient-facing exposure')
    if not any(r['kind']=='ai_dataflow' for r in linked):blockers.append('Document the data and dependency map')
    if case['data'].get('autonomy') in {'bounded_actions','consequential_actions'} and not any(r['kind']=='ai_agent' for r in linked):blockers.append('Document agent permissions, approval enforcement and revocation')
    valid=[]
    for r in linked:
        if r['kind'] not in {'ai_review','ai_evaluation'} or r['status']!='completed' or r['data'].get('calculated',{}).get('context_hash')!=scope:continue
        ids=r['data'].get('evidence_ids',[])
        if not ids:continue
        try:require_verified_evidence(db,org,ids)
        except HTTPException:continue
        valid.append(r)
    reviews={r['data'].get('domain') for r in valid if r['kind']=='ai_review' and r['data'].get('result')=='satisfactory'}
    for domain in sorted(required-reviews):blockers.append('Current completed '+domain+' review with verified evidence is required')
    families={'ordinary_workflow','human_review','resilience'}
    if case['data'].get('risk_tier') in {'high','critical'} or case['data'].get('autonomy')!='draft_only':families|={'authorization','adversarial'}
    if 'clinical' in required:families.add('clinical')
    passing={r['data'].get('family') for r in valid if r['kind']=='ai_evaluation' and r['data'].get('result')=='pass'}
    for family in sorted(families-passing):blockers.append('Current passing '+family+' evaluation with verified evidence is required')
    for r in linked:
        if r['kind']=='ai_event' and r['status'] not in {'completed','closed'} and (r['data'].get('event_type')=='material_change' or r['data'].get('severity') in {'high','critical'}):blockers.append('Resolve event: '+r['title'])
        if r['kind']=='ai_evaluation' and r['status']!='closed' and r['data'].get('calculated',{}).get('context_hash')==scope and r['data'].get('result')=='fail' and r['data'].get('severity') in {'high','critical'}:blockers.append('Close and retest release-blocking evaluation: '+r['title'])
        if r['kind']=='ai_exception' and r['status'] in {'approved','active'} and r['data'].get('expires_on','')<today:blockers.append('Expired exception: '+r['title'])
    baseline=[{'id':r['id'],'version':r['version'],'status':r['status']} for r in linked if r['kind'] in {'ai_review','ai_evaluation','ai_exception'}]
    return {'ready_for_human_release_review':not blockers,'blockers':blockers,'context_hash':scope,'readiness_hash':digest({'context':scope,'evidence_records':sorted(baseline,key=lambda r:r['id'])}),'required_reviews':sorted(required),'required_test_families':sorted(families)}

def approve(db,org,record):
    from .store import get,fail,require_verified_evidence
    data=record['data'];case=get(db,org,data['use_case_id'],'ai_use_case')
    if data.get('calculated',{}).get('context_hash')!=context_hash(case,rows(db,org)):fail('Configuration changed; reopen and review this decision again',409)
    if record['kind']=='ai_decision' and data['decision_type']=='release' and data['outcome'] in {'permitted','restricted'}:
        state=readiness(db,org,case)
        if state['blockers']:fail('Release hold: '+'; '.join(state['blockers']),409)
        if data.get('calculated',{}).get('readiness_hash')!=state['readiness_hash']:fail('Review evidence changed; reopen this decision before signing',409)
        if not data.get('evidence_ids'):fail('Attach verified release-packet evidence')
        require_verified_evidence(db,org,data['evidence_ids'])

def overview(db,user,org):
    from .store import access,require_verified_evidence
    from fastapi import HTTPException
    access(db,user,org);records=rows(db,org);cases=[r for r in records if r['kind']=='ai_use_case'];result=[];today=date.today().isoformat()
    for case in cases:
        state=readiness(db,org,case,records)
        decisions=[r for r in records if r['kind']=='ai_decision' and r['data'].get('use_case_id')==case['id'] and r['data'].get('decision_type')=='release' and r['status'] in {'approved','active','closed','rejected'}]
        decision=decisions[-1] if decisions else None
        authorized=bool(decision and decision['status'] in {'approved','active'} and decision['data'].get('outcome') in {'permitted','restricted'} and decision['data'].get('expires_on','')>=today and decision['data'].get('calculated',{}).get('readiness_hash')==state['readiness_hash'] and not state['blockers'])
        if authorized:
            try:
                if not decision['data'].get('evidence_ids'):authorized=False
                else:require_verified_evidence(db,org,decision['data']['evidence_ids'])
            except HTTPException:authorized=False
        result.append({'id':case['id'],'title':case['title'],'owner':case['data'].get('business_owner'),'risk_tier':case['data'].get('risk_tier'),'review_on':case['data'].get('review_on'),'authorization':decision['data']['stage'] if authorized else 'not_authorized','decision_id':decision['id'] if decision else None,**state})
    return {'cases':result,'counts':{kind:sum(r['kind']==kind for r in records) for kind in AI_MODULES},'note':'Readiness is a release checklist, never automatic approval. Authorization applies to the reviewed baseline and current evidence. This workspace tracks governance; it does not execute AI tools or stop external systems.','source':{'page_id':'2710be56313383029852016a4e6cb6e7','snapshot':'2026-10-28','live_sync':False}}
