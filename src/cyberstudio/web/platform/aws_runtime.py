"""Runtime IAM credentials only; no AWS credentials are stored by the application."""
from functools import lru_cache
import os
import boto3
from botocore.config import Config

@lru_cache(maxsize=16)
def client(service,region=None):
    return boto3.client(service,region_name=region or os.getenv('AWS_REGION',os.getenv('AWS_DEFAULT_REGION','us-east-2')),config=Config(retries={'total_max_attempts':3,'mode':'standard'},connect_timeout=4,read_timeout=12))
