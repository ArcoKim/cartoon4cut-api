import boto3
import json
import os

bucket = os.getenv("BUCKET_NAME")
prefix = 'origin/'  

client = boto3.client('s3')
result = client.list_objects(Bucket=bucket, Prefix=prefix, Delimiter='/')

def lambda_handler(event, context):
    query = event["queryStringParameters"]
    
    ret = []
    for o in result.get('CommonPrefixes'):
        name = o.get('Prefix').split('/')[1]
        if query != None and "image" in query and query["image"] == "true":
            ret.append({
                "name": name,
                "image": f"https://{bucket}.s3.ap-northeast-2.amazonaws.com/transformed/{name}/preview.png"
            })
        else:
            ret.append(name)
    
    return {
        "statusCode": 200,
        "body": json.dumps(ret)
    }