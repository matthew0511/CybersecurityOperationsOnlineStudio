"""Additive platform resources and staged runtime wiring. No secret values."""
import json
from pathlib import Path
ROOT=Path(__file__).parent
R=lambda x:{'Ref':x}
S=lambda x:{'Fn::Sub':x}
A=lambda x,y:{'Fn::GetAtt':[x,y]}
allow=lambda a,r:{'Effect':'Allow','Action':a,'Resource':r}
assume=lambda s:{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':s},'Action':'sts:AssumeRole','Condition':{'StringEquals':{'aws:SourceAccount':R('AWS::AccountId')}}}]}
resources={}
def add(n,t,p,**kw):resources[n]={'Type':t,'Properties':p,**kw}
tags=[{'Key':'Project','Value':'Cyber Security Operations Online Studio'}]
for n,username in [('AuthKey',None),('PlatformDatabase', 'studioapp_platform')]:
    gen={'PasswordLength':48,'ExcludePunctuation':True}
    if username:gen.update(SecretStringTemplate=json.dumps({'username':username}),GenerateStringKey='password')
    add(n,'AWS::SecretsManager::Secret',{'Description':'Online Studio platform '+n,'GenerateSecretString':gen,'Tags':tags},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
add('ScanBucket','AWS::S3::Bucket',{'PublicAccessBlockConfiguration':{'BlockPublicAcls':True,'BlockPublicPolicy':True,'IgnorePublicAcls':True,'RestrictPublicBuckets':True},'BucketEncryption':{'ServerSideEncryptionConfiguration':[{'ServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]},'VersioningConfiguration':{'Status':'Enabled'},'LifecycleConfiguration':{'Rules':[{'Id':'ExpireScanCopies','Status':'Enabled','Prefix':'uploads/','ExpirationInDays':7,'NoncurrentVersionExpiration':{'NoncurrentDays':7}}]},'Tags':tags},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
add('ScanPolicy','AWS::S3::BucketPolicy',{'Bucket':R('ScanBucket'),'PolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Deny','Principal':'*','Action':'s3:*','Resource':[A('ScanBucket','Arn'),S('${ScanBucket.Arn}/*')],'Condition':{'Bool':{'aws:SecureTransport':'false'}}}]}})
rule=S('arn:${AWS::Partition}:events:${AWS::Region}:${AWS::AccountId}:rule/DO-NOT-DELETE-AmazonGuardDutyMalwareProtectionS3*')
stm=[dict(allow(['events:PutRule','events:DeleteRule','events:PutTargets','events:RemoveTargets'],rule),Condition={'StringEquals':{'events:ManagedBy':'malware-protection-plan.guardduty.amazonaws.com'}}),allow(['events:DescribeRule','events:ListTargetsByRule'],rule),allow(['s3:GetObjectTagging','s3:PutObjectTagging','s3:GetObjectVersionTagging','s3:PutObjectVersionTagging','s3:GetObject','s3:GetObjectVersion'],S('${ScanBucket.Arn}/*')),allow(['s3:GetBucketNotification','s3:PutBucketNotification','s3:ListBucket'],A('ScanBucket','Arn')),allow(['s3:PutObject'],S('${ScanBucket.Arn}/malware-protection-resource-validation-object'))]
add('ScanRole','AWS::IAM::Role',{'AssumeRolePolicyDocument':assume('malware-protection-plan.guardduty.amazonaws.com'),'Policies':[{'PolicyName':'ManagedScanner','PolicyDocument':{'Version':'2012-10-17','Statement':stm}}],'Tags':tags})
add('Scanner','AWS::GuardDuty::MalwareProtectionPlan',{'Role':A('ScanRole','Arn'),'ProtectedResource':{'S3Bucket':{'BucketName':R('ScanBucket'),'ObjectPrefixes':['uploads/']}},'Actions':{'Tagging':{'Status':'ENABLED'}},'Tags':tags})
add('Alerts','AWS::SNS::Topic',{'DisplayName':'Online Studio operations','KmsMasterKeyId':'alias/aws/sns','Tags':tags})
template={'AWSTemplateFormatVersion':'2010-09-09','Description':'Online Studio platform security keys, versioned malware quarantine and operations alert destination','Resources':resources,'Outputs':{n:{'Value':R(n)} for n in ['AuthKey','PlatformDatabase','ScanBucket','Alerts']}}
(ROOT/'platform-security.json').write_text(json.dumps(template,indent=2)+'\n')
t=json.loads((ROOT/'platform-runtime-base.json').read_text());p=t['Parameters'];rr=t['Resources']
for name in ['PlatformDbSecretArn','AuthKeySecretArn','ScanBucketName']:p[name]={'Type':'String'}
p['EnablePlatform']={'Type':'String','Default':'false','AllowedValues':['true','false']}
t['Conditions']['PlatformEnabled']={'Fn::Equals':[R('EnablePlatform'),'true']}
for name in ['RuntimeExecutionRole','MigrationExecutionRole']:
    statements=rr[name]['Properties']['Policies'][0]['PolicyDocument']['Statement']
    statements.append(allow(['secretsmanager:GetSecretValue'],[R('PlatformDbSecretArn'),R('AuthKeySecretArn')]))
rr['ApplicationTaskRole']['Properties']['Policies']=[{'PolicyName':'PlatformRuntime','PolicyDocument':{'Version':'2012-10-17','Statement':[allow(['s3:PutObject','s3:GetObjectVersionTagging'],S('arn:${AWS::Partition}:s3:::${ScanBucketName}/uploads/*')),allow(['ses:GetEmailIdentity','ses:SendEmail'],S('arn:${AWS::Partition}:ses:${AWS::Region}:${AWS::AccountId}:identity/cybersecurityoperationstudio.com'))]}}]
for name in ['ApplicationTask','MigrationTask']:
    c=rr[name]['Properties']['ContainerDefinitions'][0]
    c['Environment'] += [{'Name':'SCAN_BUCKET','Value':R('ScanBucketName')},{'Name':'PUBLIC_ORIGIN','Value':'https://cybersecurityoperationstudio.com'},{'Name':'AWS_REGION','Value':R('AWS::Region')}]
    for secret in c['Secrets']:
        if secret['Name'] in ['DB_USER','DB_PASSWORD']:
            field='username' if secret['Name']=='DB_USER' else 'password'
            new=S('${PlatformDbSecretArn}:'+field+'::')
            secret['ValueFrom']=new if name=='MigrationTask' else {'Fn::If':['PlatformEnabled',new,secret['ValueFrom']]}
    c['Secrets'].append({'Name':'AUTH_ENCRYPTION_KEY','ValueFrom':R('AuthKeySecretArn')})
(ROOT/'platform-runtime.json').write_text(json.dumps(t,indent=2)+'\n')
