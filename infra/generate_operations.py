"""Restore validation executor and native service alarms; accepts only infrastructure identifiers."""
import json
from pathlib import Path
R=lambda x:{'Ref':x}
S=lambda x:{'Fn::Sub':x}
A=lambda x,y:{'Fn::GetAtt':[x,y]}
allow=lambda a,r:{'Effect':'Allow','Action':a,'Resource':r}
assume=lambda s:{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':s},'Action':'sts:AssumeRole'}]}
params={k:{'Type':'String'} for k in ['RestoreTaskArn','MigrationExecutionRoleArn','ApplicationTaskRoleArn','LogKeyArn','SourceDbId','SourceDbHost','AppSubnets','TaskSecurityGroup','ReleaseCommit','AlertsArn','LoadBalancerName','TargetGroupName']}
params['RestoreScheduleState']={'Type':'String','Default':'DISABLED','AllowedValues':['DISABLED','ENABLED']}
resources={}
def add(n,t,p,**kw):resources[n]={'Type':t,'Properties':p,**kw}
add('RestoreLogs','AWS::Logs::LogGroup',{'LogGroupName':'/aws/codebuild/cyber-ops-online-studio-restore','RetentionInDays':30,'KmsKeyId':R('LogKeyArn')},DeletionPolicy='Retain',UpdateReplacePolicy='Retain')
source=S('arn:${AWS::Partition}:rds:${AWS::Region}:${AWS::AccountId}:db:${SourceDbId}');clone=S('arn:${AWS::Partition}:rds:${AWS::Region}:${AWS::AccountId}:db:studio-restore-*')
stm=[allow(['logs:CreateLogStream','logs:PutLogEvents'],S('${RestoreLogs.Arn}:*')),allow(['rds:DescribeDBInstances'],[source,clone]),allow(['rds:RestoreDBInstanceToPointInTime'],[source,clone]),allow(['rds:AddTagsToResource'],clone),dict(allow(['rds:DeleteDBInstance'],clone),Condition={'StringEquals':{'aws:ResourceTag/Purpose':'restore-validation'}}),dict(allow(['ecs:RunTask'],R('RestoreTaskArn')),Condition={'ArnEquals':{'ecs:cluster':S('arn:${AWS::Partition}:ecs:${AWS::Region}:${AWS::AccountId}:cluster/cyber-ops-online-studio-dev')}}),allow(['ecs:DescribeTasks'],S('arn:${AWS::Partition}:ecs:${AWS::Region}:${AWS::AccountId}:task/cyber-ops-online-studio-dev/*')),dict(allow(['iam:PassRole'],[R('MigrationExecutionRoleArn'),R('ApplicationTaskRoleArn')]),Condition={'StringEquals':{'iam:PassedToService':'ecs-tasks.amazonaws.com'}})]
add('RestoreRole','AWS::IAM::Role',{'AssumeRolePolicyDocument':assume('codebuild.amazonaws.com'),'Policies':[{'PolicyName':'IsolatedRestoreOnly','PolicyDocument':{'Version':'2012-10-17','Statement':stm}}]})
env={'SOURCE_DB_ID':R('SourceDbId'),'SOURCE_DB_HOST':R('SourceDbHost'),'ECS_CLUSTER':'cyber-ops-online-studio-dev','RESTORE_TASK':R('RestoreTaskArn'),'APP_SUBNETS':R('AppSubnets'),'TASK_SECURITY_GROUP':R('TaskSecurityGroup')}
buildspec='version: 0.2\nphases:\n  install:\n    commands:\n      - python -m pip install boto3\n  build:\n    commands:\n      - python scripts/restore_validation.py\n'
add('RestoreProject','AWS::CodeBuild::Project',{'Name':'cyber-ops-online-studio-restore','ServiceRole':A('RestoreRole','Arn'),'TimeoutInMinutes':60,'QueuedTimeoutInMinutes':15,'ConcurrentBuildLimit':1,'Source':{'Type':'GITHUB','Location':'https://github.com/matthew0511/CybersecurityOperationsOnlineStudio.git','BuildSpec':buildspec},'SourceVersion':R('ReleaseCommit'),'Artifacts':{'Type':'NO_ARTIFACTS'},'Environment':{'Type':'LINUX_CONTAINER','ComputeType':'BUILD_GENERAL1_SMALL','Image':'aws/codebuild/standard:7.0','PrivilegedMode':False,'EnvironmentVariables':[{'Name':k,'Value':v} for k,v in env.items()]},'LogsConfig':{'CloudWatchLogs':{'Status':'ENABLED','GroupName':R('RestoreLogs'),'StreamName':'restore'}}})
add('ScheduleRole','AWS::IAM::Role',{'AssumeRolePolicyDocument':assume('events.amazonaws.com'),'Policies':[{'PolicyName':'StartOnlyRestoreProject','PolicyDocument':{'Version':'2012-10-17','Statement':[allow(['codebuild:StartBuild'],A('RestoreProject','Arn'))]}}]})
add('RestoreSchedule','AWS::Events::Rule',{'Description':'Monthly isolated PITR restore and read-only verification; never directs production traffic','ScheduleExpression':'cron(0 4 1 * ? *)','State':R('RestoreScheduleState'),'Targets':[{'Id':'Restore','Arn':A('RestoreProject','Arn'),'RoleArn':A('ScheduleRole','Arn')}]})
add('RestoreFailureRule','AWS::Events::Rule',{'EventPattern':{'source':['aws.codebuild'],'detail-type':['CodeBuild Build State Change'],'detail':{'project-name':['cyber-ops-online-studio-restore'],'build-status':['FAILED','FAULT','TIMED_OUT']}},'Targets':[{'Id':'OperationsAlert','Arn':R('AlertsArn')}]})
def alarm(name,namespace,metric,dimensions,stat,threshold,operator='GreaterThanThreshold',missing='notBreaching'):
    add(name,'AWS::CloudWatch::Alarm',{'AlarmName':'studio-'+name,'AlarmDescription':'Online Studio operational check. Configure and confirm SNS subscribers for external delivery.','Namespace':namespace,'MetricName':metric,'Dimensions':[{'Name':k,'Value':v} for k,v in dimensions.items()],'Statistic':stat,'Period':60,'EvaluationPeriods':3,'DatapointsToAlarm':2,'Threshold':threshold,'ComparisonOperator':operator,'TreatMissingData':missing,'AlarmActions':[R('AlertsArn')],'OKActions':[R('AlertsArn')]})
ecs={'ClusterName':'cyber-ops-online-studio-dev','ServiceName':'cyber-ops-online-studio-web'}
alarm('ServiceCPU','AWS/ECS','CPUUtilization',ecs,'Average',85)
alarm('ServiceMemory','AWS/ECS','MemoryUtilization',ecs,'Average',85)
alarm('UnhealthyTargets','AWS/ApplicationELB','UnHealthyHostCount',{'LoadBalancer':R('LoadBalancerName'),'TargetGroup':R('TargetGroupName')},'Maximum',0)
alarm('NoHealthyTargets','AWS/ApplicationELB','HealthyHostCount',{'LoadBalancer':R('LoadBalancerName'),'TargetGroup':R('TargetGroupName')},'Minimum',1,'LessThanThreshold','breaching')
alarm('TargetErrors','AWS/ApplicationELB','HTTPCode_Target_5XX_Count',{'LoadBalancer':R('LoadBalancerName'),'TargetGroup':R('TargetGroupName')},'Sum',5)
alarm('DatabaseCPU','AWS/RDS','CPUUtilization',{'DBInstanceIdentifier':R('SourceDbId')},'Average',85)
alarm('DatabaseStorage','AWS/RDS','FreeStorageSpace',{'DBInstanceIdentifier':R('SourceDbId')},'Minimum',5*1024**3,'LessThanThreshold')
Path(__file__).with_name('platform-operations.json').write_text(json.dumps({'AWSTemplateFormatVersion':'2010-09-09','Description':'Online Studio native service alarms and bounded monthly isolated restore validation','Parameters':params,'Resources':resources,'Outputs':{'RestoreProject':{'Value':R('RestoreProject')}}},indent=2)+'\n')
