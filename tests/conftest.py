import os
import boto3
import pytest
from moto import mock_aws

@pytest.fixture(autouse=True)
def fake_s3():
    with mock_aws():
        os.environ.setdefault("AWS_REGION", "us-east-1")
        os.environ.setdefault("S3_BUCKET", "test-bucket")
        s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
        if "test-bucket" not in [b["Name"] for b in s3.list_buckets().get("Buckets", [])]:
            s3.create_bucket(Bucket=os.environ["S3_BUCKET"])
        yield
