# tests/conftest.py
import os

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws


@pytest.fixture(autouse=True)
def fake_s3():
    with mock_aws():
        # Ortamı zorla sabitle
        region = os.environ.get("AWS_REGION", "us-east-1")
        bucket = os.environ.get("S3_BUCKET", "test-bucket")
        os.environ["AWS_REGION"] = region
        os.environ["S3_BUCKET"] = bucket

        s3 = boto3.client("s3", region_name=region)

        try:
            if region == "us-east-1":
                # us-east-1 için LocationConstraint verilmez
                s3.create_bucket(Bucket=bucket)
            else:
                # Diğer tüm bölgelerde LocationConstraint zorunlu
                s3.create_bucket(
                    Bucket=bucket,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            # Test tekrarlarında bucket var olabilir; sessiz geç
            if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                raise

        yield
