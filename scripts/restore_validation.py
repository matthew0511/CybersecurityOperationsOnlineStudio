"""Isolated RDS PITR verification orchestrator. No secret values are read here."""
import os,time,uuid,json
import boto3
from botocore.config import Config


def main():
    region=os.environ.get('AWS_REGION','us-east-2');session=boto3.Session(region_name=region)
    cfg=Config(retries={'total_max_attempts':3,'mode':'standard'},connect_timeout=5,read_timeout=20)
    rds=session.client('rds',config=cfg);ecs=session.client('ecs',config=cfg)
    source=os.environ['SOURCE_DB_ID'];target='studio-restore-'+uuid.uuid4().hex[:16]
    database=rds.describe_db_instances(DBInstanceIdentifier=source)['DBInstances'][0]
    if target==source or not target.startswith('studio-restore-'):raise ValueError('Refusing an unsafe restore target')
    created=False
    try:
        rds.restore_db_instance_to_point_in_time(SourceDBInstanceIdentifier=source,TargetDBInstanceIdentifier=target,UseLatestRestorableTime=True,DBInstanceClass=database['DBInstanceClass'],MultiAZ=False,PubliclyAccessible=False,DBSubnetGroupName=database['DBSubnetGroup']['DBSubnetGroupName'],VpcSecurityGroupIds=[s['VpcSecurityGroupId'] for s in database['VpcSecurityGroups']],DeletionProtection=False,Tags=[{'Key':'Purpose','Value':'restore-validation'},{'Key':'Project','Value':'Cyber Security Operations Online Studio'}])
        created=True;rds.get_waiter('db_instance_available').wait(DBInstanceIdentifier=target,WaiterConfig={'Delay':20,'MaxAttempts':90})
        clone=rds.describe_db_instances(DBInstanceIdentifier=target)['DBInstances'][0]
        overrides={'containerOverrides':[{'name':'studio','command':['python','-m','cyberstudio.web.platform.restore_verify'],'environment':[{'name':'SOURCE_DB_HOST','value':os.environ['SOURCE_DB_HOST']},{'name':'RESTORE_DB_HOST','value':clone['Endpoint']['Address']},{'name':'RESTORE_DB_ID','value':target},{'name':'SOURCE_DB_ID','value':source}]}]}
        result=ecs.run_task(cluster=os.environ['ECS_CLUSTER'],taskDefinition=os.environ['RESTORE_TASK'],launchType='FARGATE',count=1,networkConfiguration={'awsvpcConfiguration':{'subnets':os.environ['APP_SUBNETS'].split(','),'securityGroups':[os.environ['TASK_SECURITY_GROUP']],'assignPublicIp':'DISABLED'}},overrides=overrides)
        if result.get('failures') or not result.get('tasks'):raise RuntimeError('Restore verification task could not start')
        arn=result['tasks'][0]['taskArn'];ecs.get_waiter('tasks_stopped').wait(cluster=os.environ['ECS_CLUSTER'],tasks=[arn],WaiterConfig={'Delay':10,'MaxAttempts':60})
        task=ecs.describe_tasks(cluster=os.environ['ECS_CLUSTER'],tasks=[arn])['tasks'][0]
        if any(c.get('exitCode')!=0 for c in task['containers']):raise RuntimeError('Isolated restore verification failed; inspect restricted migration logs')
        print(json.dumps({'restore_validation':'passed','source':source,'isolated_target':target,'verification_task':arn,'cleanup':'requested'}))
    finally:
        if created:
            rds.delete_db_instance(DBInstanceIdentifier=target,SkipFinalSnapshot=True,DeleteAutomatedBackups=True)
            print('Disposable isolated restore database deletion requested; authoritative source and backups retained.')

if __name__=='__main__':main()
