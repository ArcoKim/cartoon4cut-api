import boto3
import botocore
import json
import os

s3 = boto3.client("s3")
bucket = os.getenv("BUCKET_NAME")
checks = ["disney", "clay", "flat2d", "real3d", "comics"]

def lambda_handler(event, context):
    body = json.loads(event["body"])
    ret = []

    for file in body:
        for check in checks:
            key = f"transformed/{check}/{file}"
            try:
                s3.head_object(Bucket=bucket, Key=key)
                ret.append(f"https://{bucket}.s3.ap-northeast-2.amazonaws.com/{key}")
            except botocore.exceptions.ClientError:
                pass
            
    return {
        "statusCode": 200,
        "body": json.dumps(ret)
    }