"""Fail-closed artifact intake backed by version-specific GuardDuty S3 verdicts."""
import hashlib,json,os,re
from .store import uid,fail,bounded,history
from .aws_runtime import client
from ..database import service


def indicators(content):
    text=content[:2*1024*1024].decode('utf-8',errors='ignore')
    result=[]
    if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',text):result.append('private_key')
    if re.search(r'\b\d{3}-\d{2}-\d{4}\b',text):result.append('possible_social_security_number')
    if re.search(r'\b(?:date of birth|DOB)\b',text,re.I) and re.search(r'\b(?:diagnosis|patient|medical record|treatment)\b',text,re.I):result.append('possible_patient_information')
    return result


def verdict(row):
    s3=client('s3');params={'Bucket':os.environ['SCAN_BUCKET'],'Key':row['object_key']}
    if row.get('object_version'):params['VersionId']=row['object_version']
    tags=s3.get_object_tagging(**params)['TagSet'];status=next((t['Value'] for t in tags if t['Key']=='GuardDutyMalwareScanStatus'),'PENDING')
    return {'NO_THREATS_FOUND':'clean','THREATS_FOUND':'malicious','UNSUPPORTED':'unsupported','ACCESS_DENIED':'scan_error','FAILED':'scan_error'}.get(status,'pending')


def submit(db,org,username,filename,content,context):
    if len(content)>5*1024*1024:fail('Evidence exceeds 5 MiB',413)
    if b'EICAR-STANDARD-ANTIVIRUS-TEST-FILE' in content:fail('Antivirus test signature detected; the upload was rejected')
    bucket=os.getenv('SCAN_BUCKET')
    if not bucket:fail('Artifact scanning is not configured; uploads remain unavailable until the scan service is activated',503)
    ident=uid();key='uploads/'+org+'/'+ident;flags=indicators(content);name=bounded(filename or 'evidence',250)
    response=client('s3').put_object(Bucket=bucket,Key=key,Body=content,ServerSideEncryption='AES256',ContentType='application/octet-stream')
    db.execute('INSERT INTO pl_quarantine(id,organization_id,filename,content,sha256,object_key,object_version,context,indicators,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)',(ident,org,name,content,hashlib.sha256(content).hexdigest(),key,response.get('VersionId',''),json.dumps(context),json.dumps(flags),username))
    row=dict(db.execute('SELECT * FROM pl_quarantine WHERE id=%s',(ident,)).fetchone());status=verdict(row)
    db.execute('UPDATE pl_quarantine SET status=%s WHERE id=%s',(status,ident))
    row['status']=status
    if status=='clean' and not flags:return release(db,row,username)
    history(db,org,ident,username,'upload:quarantined',{'filename':name,'status':status,'indicators':flags})
    return {'pending':True,'quarantine_id':ident,'status':status,'sensitive_indicators':flags,'message':'Artifact is quarantined. A clean scan and any required owner sensitivity review must complete before release.'}


def release(db,row,username,override_reason=''):
    org=row['organization_id']
    locked=db.execute('SELECT * FROM pl_quarantine WHERE organization_id=%s AND id=%s FOR UPDATE',(org,row['id'])).fetchone()
    if not locked:fail('Quarantined upload not found',404)
    row=dict(locked)
    if row['result']:return row['result']
    status=verdict(row)
    if status!='clean':fail('Only an independently clean scan verdict can release this artifact',409)
    if row['indicators'] and len(override_reason.strip())<20:fail('Sensitive-data indicators require an owner-reviewed justification of at least 20 characters',409)
    context=row['context'];svc=service(db)
    eid=svc.add_evidence(org,context.get('title',row['filename']),row['filename'],bytes(row['content']),context.get('mime_type','application/octet-stream'),context.get('expires_on',''))
    if context.get('assessment'):
        svc._exists('assessments',context['assessment'],org)
        if not db.execute('SELECT 1 FROM assessment_questions WHERE organization_id=%s AND assessment_id=%s AND code=%s',(org,context['assessment'],context['code'])).fetchone():fail('Assessment question no longer exists',409)
        svc.link_evidence(org,eid,'assessment',context['assessment'],'Quarantine release for '+context['code'])
        db.execute('INSERT INTO xp_question_evidence(organization_id,assessment_id,code,evidence_id) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING',(org,context['assessment'],context['code'],eid))
    group=context.get('group_id') or eid
    previous=None
    if context.get('group_id'):
        prior=db.execute('SELECT * FROM pl_evidence_versions WHERE organization_id=%s AND group_id=%s ORDER BY created_at DESC LIMIT 1',(org,group)).fetchone()
        if not prior:fail('Evidence version group not found in this organization',404)
        previous=prior['id']
    db.execute('INSERT INTO pl_evidence_versions(id,organization_id,group_id,evidence_id,sha256,supersedes,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s)',(uid(),org,group,eid,row['sha256'],previous,username))
    db.execute("UPDATE pl_quarantine SET status='released',result=%s WHERE id=%s",(eid,row['id']))
    history(db,org,eid,username,'upload:released',{'quarantine_id':row['id'],'sha256':row['sha256'],'sensitivity_override':override_reason,'scan_version':row['object_version']})
    return eid


def poll(db,org,username):
    rows=db.execute("SELECT * FROM pl_quarantine WHERE organization_id=%s AND status IN ('pending','clean') ORDER BY created_at LIMIT 25",(org,)).fetchall()
    for raw in rows:
        row=dict(raw);status=verdict(row)
        db.execute('UPDATE pl_quarantine SET status=%s WHERE id=%s',(status,row['id']))
        if status=='clean' and not row['indicators']:release(db,row,username)
