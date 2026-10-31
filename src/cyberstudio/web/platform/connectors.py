"""Outbound connectors use fixed provider origins, encrypted secrets, bounded pages and staged imports."""
import hashlib,json,re,time
from urllib.parse import quote,urlparse
import httpx
from .store import fail,bounded,uid,history
from .security import seal,unseal

PROVIDERS={
 'intune':dict(name='Microsoft Intune',fields=['tenant_id','client_id'],secrets=['client_secret'],permission='DeviceManagementManagedDevices.Read.All',mode='pull',destination='asset'),
 'defender':dict(name='Microsoft Defender',fields=['tenant_id','client_id'],secrets=['client_secret'],permission='SecurityIncident.Read.All',mode='pull',destination='incident'),
 'notion':dict(name='Notion',fields=['data_source_id','title_property'],secrets=['token'],permission='Read selected shared data source; write only on explicit publish',mode='pull_push',destination='asset'),
 'jira':dict(name='Jira Cloud',fields=['subdomain','email','project'],secrets=['api_token'],permission='Read/create issues in the selected project',mode='pull_push',destination='incident'),
 'zendesk':dict(name='Zendesk',fields=['subdomain','email'],secrets=['api_token'],permission='Read/create tickets accessible to the scoped agent',mode='pull_push',destination='incident'),
 'github':dict(name='GitHub',fields=['owner','repository'],secrets=['token'],permission='Fine-grained issues read/write for one repository',mode='pull_push',destination='incident'),
 'tenable':dict(name='Tenable Vulnerability Management',fields=[],secrets=['access_key','secret_key'],permission='Vulnerability read in your Tenable account',mode='pull',destination='incident'),
 'slack':dict(name='Slack',fields=['channel'],secrets=['bot_token'],permission='chat:write to the approved channel',mode='notify',destination=None),
 'teams':dict(name='Microsoft Teams via Graph',fields=['tenant_id','client_id','team_id','channel_id'],secrets=['client_secret'],permission='Approved Graph channel message permission; provider consent may restrict app-only sends',mode='notify',destination=None),
 'ses':dict(name='Amazon SES',fields=['region','sender'],secrets=[],permission='Runtime IAM ses:SendEmail; verified identity and production/sandbox recipient rules',mode='notify',destination=None),
}


def validate_config(provider,config,secrets_):
    definition=PROVIDERS.get(provider)
    if not definition:fail('Unsupported integration provider')
    if not isinstance(config,dict) or set(config)-set(definition['fields']):fail('Unsupported provider configuration')
    for name in definition['fields']:
        if not isinstance(config.get(name),str) or not config[name].strip():fail('Enter '+name.replace('_',' '))
        bounded(config[name],500)
    for name in ['tenant_id','client_id','data_source_id','team_id']:
        if name in config and not re.fullmatch(r'[0-9a-fA-F-]{32,36}',config[name]):fail('Use the provider GUID for '+name)
    for name in ['subdomain','owner','repository']:
        if name in config and not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',config[name]):fail('Use a simple provider identifier for '+name)
    if provider=='jira' and not re.fullmatch(r'[A-Z][A-Z0-9_]{1,20}',config['project']):fail('Use a Jira project key')
    if provider=='ses' and (not re.fullmatch(r'[a-z]{2}-[a-z]+-\d',config['region']) or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',config['sender'])):fail('Choose a region and verified sender address')
    if not isinstance(secrets_,dict) or set(secrets_)-set(definition['secrets']):fail('Unsupported credential field')
    for key in definition['secrets']:
        if not isinstance(secrets_.get(key),str) or not secrets_[key] or len(secrets_[key])>12000:fail('Enter '+key.replace('_',' '))
    return {k:v.strip() for k,v in config.items()}


def public(row):
    result={k:v for k,v in dict(row).items() if k!='secret_cipher'}
    result['credentials_saved']=bool(row.get('secret_cipher'))
    return result


def save(db,user,org,body):
    from ..experience import require_owner
    from .store import access
    access(db,user,org,True,'integrations:manage');require_owner(user)
    previous=db.execute('SELECT * FROM pl_integrations WHERE organization_id=%s AND id=%s',(org,body.get('id',''))).fetchone()
    if body.get('id') and not previous:fail('Integration not found',404)
    provider=body.get('provider')
    if previous and provider!=previous['provider']:fail('Provider cannot change on an existing connection')
    credentials=json.loads(unseal(previous['secret_cipher'])) if previous and previous['secret_cipher'] else {}
    credentials.update({k:v for k,v in body.get('credentials',{}).items() if v})
    config=validate_config(provider,body.get('config',{}),credentials)
    ident=previous['id'] if previous else uid();name=bounded(body.get('name',PROVIDERS[provider]['name']),150)
    if not name:fail('Name the connection')
    # Saving credentials never enables automatic external actions.
    db.execute('''INSERT INTO pl_integrations(id,organization_id,provider,name,config,secret_cipher,created_by) VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s)
     ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name,config=EXCLUDED.config,secret_cipher=EXCLUDED.secret_cipher,enabled=FALSE,connection_status='not_tested',updated_at=CURRENT_TIMESTAMP''',(ident,org,provider,name,json.dumps(config),seal(json.dumps(credentials)),user['username']))
    history(db,org,ident,user['username'],'integration:configured',{'provider':provider,'credential_values':'redacted'})
    return public(dict(db.execute('SELECT * FROM pl_integrations WHERE id=%s',(ident,)).fetchone()))


class Adapter:
    def __init__(self,row,transport=None):
        self.provider=row['provider'];self.cfg=row['config'];self.credentials=json.loads(unseal(row['secret_cipher']));self.transport=transport
    def __enter__(self):
        self.client=httpx.Client(timeout=httpx.Timeout(20,connect=5),follow_redirects=False,transport=self.transport,limits=httpx.Limits(max_connections=4));return self
    def __exit__(self,*args):self.client.close()
    def request(self,method,url,**kwargs):
        # Every adapter builds URLs from validated identifiers and fixed provider origins.
        r=self.client.request(method,url,**kwargs)
        if r.status_code==429:fail('Provider rate limit reached; retry the job later',503)
        if not 200<=r.status_code<300:fail(f'Provider request failed (HTTP {r.status_code}); review scopes and account configuration',502)
        if len(r.content)>8*1024*1024:fail('Provider page exceeded the safe import size',502)
        return r.json() if r.content else {}
    def graph(self):
        c=self.cfg;s=self.credentials
        data=self.request('POST','https://login.microsoftonline.com/'+c['tenant_id']+'/oauth2/v2.0/token',data=dict(client_id=c['client_id'],client_secret=s['client_secret'],grant_type='client_credentials',scope='https://graph.microsoft.com/.default'))
        return {'Authorization':'Bearer '+data['access_token']}
    def identity(self):
        p=self.provider;c=self.cfg;s=self.credentials
        if p in {'intune','defender','teams'}:
            headers=self.graph();path={'intune':'deviceManagement/managedDevices?$top=1','defender':'security/incidents?$top=1','teams':'teams/'+quote(c.get('team_id',''),safe='')+'/channels'}[p]
            self.request('GET','https://graph.microsoft.com/v1.0/'+path,headers=headers)
        elif p=='notion':self.request('GET','https://api.notion.com/v1/users/me',headers={'Authorization':'Bearer '+s['token'],'Notion-Version':'2025-09-03'})
        elif p=='github':self.request('GET','https://api.github.com/repos/'+c['owner']+'/'+c['repository'],headers=self.headers())
        elif p=='jira':self.request('GET','https://'+c['subdomain']+'.atlassian.net/rest/api/3/myself',auth=(c['email'],s['api_token']))
        elif p=='zendesk':self.request('GET','https://'+c['subdomain']+'.zendesk.com/api/v2/users/me.json',auth=(c['email']+'/token',s['api_token']))
        elif p=='tenable':self.request('GET','https://cloud.tenable.com/session',headers=self.headers())
        elif p=='slack':
            result=self.request('POST','https://slack.com/api/auth.test',headers=self.headers())
            if not result.get('ok'):fail('Slack authentication was not accepted',502)
        elif p=='ses':
            from .aws_runtime import client
            r=client('sesv2',c['region']).get_email_identity(EmailIdentity=c['sender'].split('@')[-1])
            if not r.get('VerifiedForSendingStatus'):fail('The SES sender domain has not been verified',409)
        return {'authenticated':True,'provider':p,'note':'Authentication checked; this does not certify every optional permission or activate synchronization.'}
    def headers(self):
        s=self.credentials
        if self.provider=='tenable':return {'X-ApiKeys':'accessKey='+s['access_key']+'; secretKey='+s['secret_key']}
        return {'Authorization':'Bearer '+s.get('token',s.get('bot_token','')),'Accept':'application/json'}
    def pull(self):
        p=self.provider;c=self.cfg;s=self.credentials;items=[];cursor=None
        if p not in {'intune','defender','notion','jira','zendesk','github','tenable'}:fail('This provider is for notifications, not record import')
        graph_headers=self.graph() if p in {'intune','defender'} else {}
        for page in range(10):
            if p in {'intune','defender'}:
                initial='https://graph.microsoft.com/v1.0/'+('deviceManagement/managedDevices?$top=100' if p=='intune' else 'security/incidents?$top=100')
                url=cursor or initial
                if urlparse(url).scheme!='https' or urlparse(url).netloc!='graph.microsoft.com':fail('Provider returned an unsafe pagination origin',502)
                data=self.request('GET',url,headers=graph_headers);batch=data.get('value',[]);cursor=data.get('@odata.nextLink')
            elif p=='notion':
                data=self.request('POST','https://api.notion.com/v1/data_sources/'+c['data_source_id']+'/query',headers={'Authorization':'Bearer '+s['token'],'Notion-Version':'2025-09-03'},json={'page_size':100,**({'start_cursor':cursor} if cursor else {})});batch=data.get('results',[]);cursor=data.get('next_cursor') if data.get('has_more') else None
            elif p=='github':
                data=self.request('GET','https://api.github.com/repos/'+c['owner']+'/'+c['repository']+'/issues',headers=self.headers(),params={'state':'all','per_page':100,'page':page+1});batch=data;cursor='more' if len(batch)==100 else None
            elif p=='zendesk':
                data=self.request('GET','https://'+c['subdomain']+'.zendesk.com/api/v2/tickets.json',auth=(c['email']+'/token',s['api_token']),params={'page':page+1,'per_page':100});batch=data.get('tickets',[]);cursor=data.get('next_page')
            elif p=='jira':
                data=self.request('GET','https://'+c['subdomain']+'.atlassian.net/rest/api/3/search/jql',auth=(c['email'],s['api_token']),params={'jql':'project = '+c['project'],'maxResults':100,**({'nextPageToken':cursor} if cursor else {})});batch=data.get('issues',[]);cursor=data.get('nextPageToken')
            else:
                data=self.request('GET','https://cloud.tenable.com/workbenches/vulnerabilities',headers=self.headers());batch=data.get('vulnerabilities',[]);cursor=None
            if not isinstance(batch,list):fail('Provider response did not contain a record list',502)
            items.extend(batch)
            if not cursor:break
        return items, bool(cursor)
    def publish(self,title,description):
        p=self.provider;c=self.cfg;s=self.credentials;title=bounded(title,250);description=bounded(description,10000)
        if p=='github':return self.request('POST','https://api.github.com/repos/'+c['owner']+'/'+c['repository']+'/issues',headers=self.headers(),json={'title':title,'body':description})
        if p=='zendesk':return self.request('POST','https://'+c['subdomain']+'.zendesk.com/api/v2/tickets.json',auth=(c['email']+'/token',s['api_token']),json={'ticket':{'subject':title,'comment':{'body':description}}})
        if p=='jira':return self.request('POST','https://'+c['subdomain']+'.atlassian.net/rest/api/3/issue',auth=(c['email'],s['api_token']),json={'fields':{'project':{'key':c['project']},'summary':title,'issuetype':{'name':'Task'},'description':{'type':'doc','version':1,'content':[{'type':'paragraph','content':[{'type':'text','text':description}]}]}}})
        if p=='notion':return self.request('POST','https://api.notion.com/v1/pages',headers={'Authorization':'Bearer '+s['token'],'Notion-Version':'2025-09-03'},json={'parent':{'type':'data_source_id','data_source_id':c['data_source_id']},'properties':{c['title_property']:{'title':[{'text':{'content':title}}]}},'children':[{'object':'block','type':'paragraph','paragraph':{'rich_text':[{'type':'text','text':{'content':description[:2000]}}]}}]})
        fail('This provider does not support publishing')
    def notify(self,title,message,recipients=None):
        p=self.provider;c=self.cfg
        if p=='slack':
            r=self.request('POST','https://slack.com/api/chat.postMessage',headers=self.headers(),json={'channel':c['channel'],'text':title+'\n'+message})
            if not r.get('ok'):fail('Slack did not accept the message',502)
            return {'accepted':True}
        if p=='teams':return self.request('POST','https://graph.microsoft.com/v1.0/teams/'+c['team_id']+'/channels/'+quote(c['channel_id'],safe='')+'/messages',headers=self.graph(),json={'body':{'contentType':'text','content':title+'\n'+message}})
        if p=='ses':
            if not recipients or len(recipients)>20 or any(not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',v) for v in recipients):fail('Choose 1–20 approved email recipients')
            from .aws_runtime import client
            response=client('sesv2',c['region']).send_email(FromEmailAddress=c['sender'],Destination={'ToAddresses':recipients},Content={'Simple':{'Subject':{'Data':title[:200],'Charset':'UTF-8'},'Body':{'Text':{'Data':message,'Charset':'UTF-8'}}}})
            return {'accepted':True,'provider_message_id':response.get('MessageId')}
        fail('Choose an email, Slack or Teams delivery connection')


def stage(db,row,items):
    staged=0
    for item in items[:1000]:
        ext=str(item.get('id',item.get('plugin_id',item.get('key',''))))[:200]
        if not ext:continue
        data=json.dumps(item,default=str)
        if len(data)>100000:continue
        digest=hashlib.sha256(data.encode()).hexdigest()
        db.execute('INSERT INTO pl_external(organization_id,integration_id,external_id,payload,source_hash) VALUES (%s,%s,%s,%s::jsonb,%s) ON CONFLICT(organization_id,integration_id,external_id) DO UPDATE SET payload=EXCLUDED.payload,source_hash=EXCLUDED.source_hash,updated_at=CURRENT_TIMESTAMP',(row['organization_id'],row['id'],ext,data,digest));staged+=1
    return staged
