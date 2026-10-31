"""Generate the CloudFormation runtime stack. Contains no credentials."""
import json
from pathlib import Path

ref=lambda value:{'Ref':value}
att=lambda value,field:{'Fn::GetAtt':[value,field]}
sub=lambda value:{'Fn::Sub':value}

buildspec='''version: 0.2
phases:
  install:
    commands:
      - python -m pip install -r requirements-web.txt pytest httpx
  pre_build:
    commands:
      - docker run --detach --name postgres-test --publish 127.0.0.1:5432:5432 --env POSTGRES_USER=studio_test --env POSTGRES_PASSWORD=synthetic-test-only --env POSTGRES_DB=studio_test postgres:18-alpine
      - timeout 90 sh -c 'until docker exec postgres-test pg_isready -U studio_test; do sleep 2; done'
      - node --test tests/ui-core.test.cjs
      - PYTHONPATH=src TEST_DATABASE_URL=postgresql://studio_test:synthetic-test-only@127.0.0.1:5432/studio_test python -m pytest -q
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $REGISTRY
  build:
    commands:
      - docker build --tag $IMAGE_URI .
      - docker run --rm --read-only --cap-drop ALL --network host --env TEST_DATABASE_URL=postgresql://studio_test:synthetic-test-only@127.0.0.1:5432/studio_test --mount type=volume,source=studio-temp,target=/tmp $IMAGE_URI python -c "import tempfile; from cyberstudio.web.database import connect; connect().execute('SELECT 1'); t=tempfile.TemporaryDirectory(); t.cleanup(); print('Read-only non-root container database and temporary-volume smoke test passed')"
      - docker push $IMAGE_URI
'''

params={k:{'Type':'String'} for k in ['VpcId','AppSubnetA','AppSubnetB','TaskSecurityGroup','DatabaseHost','MasterSecretArn','RepositoryUri','ImageTag']}
params['DeployService']={'Type':'String','Default':'false','AllowedValues':['true','false']}
resources={}
def add(name,kind,props,**extra):
    resources[name]={'Type':kind,'Properties':props,**extra}

tags=[{'Key':'Project','Value':'Cyber Security Operations Online Studio'},{'Key':'Environment','Value':'dev'}]
assume=lambda svc:{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':svc},'Action':'sts:AssumeRole'}]}
policy=lambda name,statements:[{'PolicyName':name,'PolicyDocument':{'Version':'2012-10-17','Statement':statements}}]
allow=lambda actions,arn:{'Effect':'Allow','Action':actions,'Resource':arn}

add('BuildBucket','AWS::S3::Bucket',{'BucketName':sub('cyber-ops-online-studio-build-${AWS::AccountId}-${AWS::Region}'),'PublicAccessBlockConfiguration':{'BlockPublicAcls':True,'BlockPublicPolicy':True,'IgnorePublicAcls':True,'RestrictPublicBuckets':True},'BucketEncryption':{'ServerSideEncryptionConfiguration':[{'ServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]},'VersioningConfiguration':{'Status':'Enabled'},'LifecycleConfiguration':{'Rules':[{'Id':'ExpireBuildSources','Status':'Enabled','Prefix':'source/','ExpirationInDays':30,'NoncurrentVersionExpiration':{'NoncurrentDays':30}}]},'Tags':tags},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
add('AuditBucket','AWS::S3::Bucket',{'BucketName':sub('cyber-ops-online-studio-audit-${AWS::AccountId}-${AWS::Region}'),'PublicAccessBlockConfiguration':{'BlockPublicAcls':True,'BlockPublicPolicy':True,'IgnorePublicAcls':True,'RestrictPublicBuckets':True},'BucketEncryption':{'ServerSideEncryptionConfiguration':[{'ServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]},'VersioningConfiguration':{'Status':'Enabled'},'Tags':tags},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
trailarn=sub('arn:${AWS::Partition}:cloudtrail:${AWS::Region}:${AWS::AccountId}:trail/cyber-ops-online-studio-management')
add('AuditBucketPolicy','AWS::S3::BucketPolicy',{'Bucket':ref('AuditBucket'),'PolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'cloudtrail.amazonaws.com'},'Action':'s3:GetBucketAcl','Resource':att('AuditBucket','Arn'),'Condition':{'StringEquals':{'aws:SourceArn':trailarn}}},{'Effect':'Allow','Principal':{'Service':'cloudtrail.amazonaws.com'},'Action':'s3:PutObject','Resource':sub('${AuditBucket.Arn}/AWSLogs/${AWS::AccountId}/*'),'Condition':{'StringEquals':{'aws:SourceArn':trailarn,'s3:x-amz-acl':'bucket-owner-full-control'}}},{'Effect':'Deny','Principal':'*','Action':'s3:*','Resource':[att('AuditBucket','Arn'),sub('${AuditBucket.Arn}/*')],'Condition':{'Bool':{'aws:SecureTransport':'false'}}}]}})
add('Trail','AWS::CloudTrail::Trail',{'TrailName':'cyber-ops-online-studio-management','S3BucketName':ref('AuditBucket'),'IsLogging':True,'IsMultiRegionTrail':True,'IncludeGlobalServiceEvents':True,'EnableLogFileValidation':True,'EventSelectors':[{'IncludeManagementEvents':True,'ReadWriteType':'All'}],'Tags':tags},DependsOn=['AuditBucketPolicy'])
add('LogsKey','AWS::KMS::Key',{'EnableKeyRotation':True,'Description':'Online Studio operational log encryption','KeyPolicy':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'AWS':sub('arn:${AWS::Partition}:iam::${AWS::AccountId}:root')},'Action':'kms:*','Resource':'*'},{'Effect':'Allow','Principal':{'Service':sub('logs.${AWS::Region}.amazonaws.com')},'Action':['kms:Encrypt','kms:Decrypt','kms:ReEncrypt*','kms:GenerateDataKey*','kms:DescribeKey'],'Resource':'*','Condition':{'ArnLike':{'kms:EncryptionContext:aws:logs:arn':sub('arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:*')}}}]}},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
for name,log in [('BuildLogs','/aws/codebuild/cyber-ops-online-studio'),('AppLogs','/ecs/cyber-ops-online-studio-web'),('ApiLogs','/aws/apigateway/cyber-ops-online-studio')]:
    add(name,'AWS::Logs::LogGroup',{'LogGroupName':log,'RetentionInDays':30,'KmsKeyId':att('LogsKey','Arn'),'Tags':tags},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
add('DatabaseSecret','AWS::SecretsManager::Secret',{'Name':'cyber-ops-online-studio-dev/application-db','Description':'Least-privilege PostgreSQL application credentials','GenerateSecretString':{'SecretStringTemplate':'{"username":"studioapp"}','GenerateStringKey':'password','PasswordLength':48,'ExcludePunctuation':True},'Tags':tags},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
add('SetupSecret','AWS::SecretsManager::Secret',{'Name':'cyber-ops-online-studio-dev/setup','Description':'One-time owner bootstrap code. Consumed by creation of the first owner account.','GenerateSecretString':{'PasswordLength':48,'ExcludePunctuation':True},'Tags':tags},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
ecrarn=sub('arn:${AWS::Partition}:ecr:${AWS::Region}:${AWS::AccountId}:repository/cyber-ops-online-studio-dev')
logactions=['logs:CreateLogStream','logs:PutLogEvents']
pull=['ecr:BatchCheckLayerAvailability','ecr:GetDownloadUrlForLayer','ecr:BatchGetImage']
push=pull+['ecr:InitiateLayerUpload','ecr:UploadLayerPart','ecr:CompleteLayerUpload','ecr:PutImage']
add('BuildRole','AWS::IAM::Role',{'AssumeRolePolicyDocument':assume('codebuild.amazonaws.com'),'Policies':policy('ScopedBuild',[allow(['s3:GetObject','s3:GetObjectVersion'],sub('${BuildBucket.Arn}/source/*')),allow(['s3:GetBucketLocation'],att('BuildBucket','Arn')),allow(logactions,sub('${BuildLogs.Arn}:*')),allow(['ecr:GetAuthorizationToken'],'*'),allow(push,ecrarn)]),'Tags':tags})
add('Builder','AWS::CodeBuild::Project',{'Name':'cyber-ops-online-studio-web','ServiceRole':att('BuildRole','Arn'),'TimeoutInMinutes':30,'QueuedTimeoutInMinutes':15,'Artifacts':{'Type':'NO_ARTIFACTS'},'Source':{'Type':'S3','Location':sub('${BuildBucket}/source/studio-web.zip'),'BuildSpec':buildspec},'Environment':{'Type':'LINUX_CONTAINER','ComputeType':'BUILD_GENERAL1_SMALL','Image':'aws/codebuild/standard:7.0','PrivilegedMode':True,'EnvironmentVariables':[{'Name':'IMAGE_URI','Value':{'Fn::Join':[':',[ref('RepositoryUri'),ref('ImageTag')]]}},{'Name':'REGISTRY','Value':sub('${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com')}]},'LogsConfig':{'CloudWatchLogs':{'Status':'ENABLED','GroupName':ref('BuildLogs'),'StreamName':'build'}},'Tags':tags})
for name,secrets in [('RuntimeExecutionRole',[ref('DatabaseSecret'),ref('SetupSecret')]),('MigrationExecutionRole',[ref('DatabaseSecret'),ref('MasterSecretArn')])]:
    add(name,'AWS::IAM::Role',{'AssumeRolePolicyDocument':assume('ecs-tasks.amazonaws.com'),'Policies':policy('ScopedExecution',[allow(pull,ecrarn),allow(['ecr:GetAuthorizationToken'],'*'),allow(logactions,sub('${AppLogs.Arn}:*')),allow(['secretsmanager:GetSecretValue'],secrets)]),'Tags':tags})
add('ApplicationTaskRole','AWS::IAM::Role',{'AssumeRolePolicyDocument':assume('ecs-tasks.amazonaws.com'),'Tags':tags})
for name,migration in [('ApplicationTask',False),('MigrationTask',True)]:
    env=[{'Name':'DB_HOST','Value':ref('DatabaseHost')},{'Name':'DB_NAME','Value':'cyberops'},{'Name':'APP_ENV','Value':'production'}]
    secrets=[{'Name':'DB_USER','ValueFrom':sub('${DatabaseSecret}:username::')},{'Name':'DB_PASSWORD','ValueFrom':sub('${DatabaseSecret}:password::')}]
    if migration:secrets += [{'Name':'DB_ADMIN_USER','ValueFrom':sub('${MasterSecretArn}:username::')},{'Name':'DB_ADMIN_PASSWORD','ValueFrom':sub('${MasterSecretArn}:password::')}]
    else:secrets += [{'Name':'SETUP_TOKEN','ValueFrom':ref('SetupSecret')}]
    container={'Name':'studio','Image':{'Fn::Join':[':',[ref('RepositoryUri'),ref('ImageTag')]]},'Essential':True,'User':'10001:10001','ReadonlyRootFilesystem':True,'LinuxParameters':{'Capabilities':{'Drop':['ALL']}},'Environment':env,'Secrets':secrets,'LogConfiguration':{'LogDriver':'awslogs','Options':{'awslogs-group':ref('AppLogs'),'awslogs-region':ref('AWS::Region'),'awslogs-stream-prefix':'migration' if migration else 'web','mode':'blocking'}},'MountPoints':[{'SourceVolume':'scratch','ContainerPath':'/tmp','ReadOnly':False}]}
    if migration:container['Command']=['python','-m','cyberstudio.web.database']
    else:
        container['PortMappings']=[{'ContainerPort':8080,'Protocol':'tcp'}]
        container['HealthCheck']={'Command':['CMD-SHELL',"python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/readyz',timeout=4)\""],'Interval':30,'Timeout':5,'Retries':3,'StartPeriod':30}
    add(name,'AWS::ECS::TaskDefinition',{'Family':'cyber-ops-online-studio-migrate' if migration else 'cyber-ops-online-studio-web','RequiresCompatibilities':['FARGATE'],'NetworkMode':'awsvpc','Cpu':'512','Memory':'1024','ExecutionRoleArn':att('MigrationExecutionRole' if migration else 'RuntimeExecutionRole','Arn'),'TaskRoleArn':att('ApplicationTaskRole','Arn'),'RuntimePlatform':{'OperatingSystemFamily':'LINUX','CpuArchitecture':'X86_64'},'Volumes':[{'Name':'scratch'}],'ContainerDefinitions':[container],'Tags':tags})
add('AlbSG','AWS::EC2::SecurityGroup',{'GroupDescription':'Internal ALB; only API Gateway VPC link can reach it','VpcId':ref('VpcId'),'SecurityGroupEgress':[{'IpProtocol':'tcp','FromPort':8080,'ToPort':8080,'DestinationSecurityGroupId':ref('TaskSecurityGroup')}],'Tags':tags})
add('LinkSG','AWS::EC2::SecurityGroup',{'GroupDescription':'API Gateway VPC link egress to internal ALB','VpcId':ref('VpcId'),'SecurityGroupEgress':[{'IpProtocol':'tcp','FromPort':80,'ToPort':80,'DestinationSecurityGroupId':ref('AlbSG')}],'Tags':tags})
add('AlbIngress','AWS::EC2::SecurityGroupIngress',{'GroupId':ref('AlbSG'),'IpProtocol':'tcp','FromPort':80,'ToPort':80,'SourceSecurityGroupId':ref('LinkSG')})
add('TaskIngress','AWS::EC2::SecurityGroupIngress',{'GroupId':ref('TaskSecurityGroup'),'IpProtocol':'tcp','FromPort':8080,'ToPort':8080,'SourceSecurityGroupId':ref('AlbSG')})
add('Alb','AWS::ElasticLoadBalancingV2::LoadBalancer',{'Scheme':'internal','Type':'application','Subnets':[ref('AppSubnetA'),ref('AppSubnetB')],'SecurityGroups':[ref('AlbSG')],'Tags':tags})
add('Target','AWS::ElasticLoadBalancingV2::TargetGroup',{'VpcId':ref('VpcId'),'Protocol':'HTTP','Port':8080,'TargetType':'ip','HealthCheckPath':'/readyz','HealthCheckIntervalSeconds':30,'HealthyThresholdCount':2,'TargetGroupAttributes':[{'Key':'deregistration_delay.timeout_seconds','Value':'30'}],'Tags':tags})
add('Listener','AWS::ElasticLoadBalancingV2::Listener',{'LoadBalancerArn':ref('Alb'),'Protocol':'HTTP','Port':80,'DefaultActions':[{'Type':'forward','TargetGroupArn':ref('Target')}]})
add('VpcLink','AWS::ApiGatewayV2::VpcLink',{'Name':'cyber-ops-online-studio-private-link','SubnetIds':[ref('AppSubnetA'),ref('AppSubnetB')],'SecurityGroupIds':[ref('LinkSG')]})
add('Api','AWS::ApiGatewayV2::Api',{'Name':'Cyber Security Operations Online Studio','ProtocolType':'HTTP'})
add('Integration','AWS::ApiGatewayV2::Integration',{'ApiId':ref('Api'),'IntegrationType':'HTTP_PROXY','IntegrationUri':ref('Listener'),'ConnectionId':ref('VpcLink'),'ConnectionType':'VPC_LINK','IntegrationMethod':'ANY','PayloadFormatVersion':'1.0','TimeoutInMillis':30000,'RequestParameters':{'overwrite:path':'$request.path'}})
add('Route','AWS::ApiGatewayV2::Route',{'ApiId':ref('Api'),'RouteKey':'$default','Target':sub('integrations/${Integration}')})
add('Stage','AWS::ApiGatewayV2::Stage',{'ApiId':ref('Api'),'StageName':'$default','AutoDeploy':True,'DefaultRouteSettings':{'ThrottlingBurstLimit':50,'ThrottlingRateLimit':25},'AccessLogSettings':{'DestinationArn':att('ApiLogs','Arn'),'Format':'{"requestId":"$context.requestId","route":"$context.routeKey","status":"$context.status","responseLength":"$context.responseLength"}'}})
add('Service','AWS::ECS::Service',{'ServiceName':'cyber-ops-online-studio-web','Cluster':'cyber-ops-online-studio-dev','TaskDefinition':ref('ApplicationTask'),'DesiredCount':2,'LaunchType':'FARGATE','PlatformVersion':'LATEST','HealthCheckGracePeriodSeconds':90,'NetworkConfiguration':{'AwsvpcConfiguration':{'Subnets':[ref('AppSubnetA'),ref('AppSubnetB')],'SecurityGroups':[ref('TaskSecurityGroup')],'AssignPublicIp':'DISABLED'}},'LoadBalancers':[{'ContainerName':'studio','ContainerPort':8080,'TargetGroupArn':ref('Target')}],'DeploymentConfiguration':{'MinimumHealthyPercent':100,'MaximumPercent':200,'DeploymentCircuitBreaker':{'Enable':True,'Rollback':True}},'Tags':tags},Condition='ServiceEnabled',DependsOn=['Listener'])
outputs={'Url':{'Value':att('Api','ApiEndpoint')},'BuildBucket':{'Value':ref('BuildBucket')},'BuildProject':{'Value':ref('Builder')},'MigrationTask':{'Value':ref('MigrationTask')},'AppTask':{'Value':ref('ApplicationTask')},'TargetGroup':{'Value':ref('Target')},'SetupSecret':{'Value':ref('SetupSecret')}}
template={'AWSTemplateFormatVersion':'2010-09-09','Description':'Online Studio web runtime, private ECS/ALB, HTTPS API Gateway, build pipeline and management audit trail','Parameters':params,'Conditions':{'ServiceEnabled':{'Fn::Equals':[ref('DeployService'),'true']}},'Resources':resources,'Outputs':outputs}
if __name__=='__main__':
    path=Path(__file__).with_name('web-stack.json')
    path.write_text(json.dumps(template,indent=2)+'\n')
    print(path)
