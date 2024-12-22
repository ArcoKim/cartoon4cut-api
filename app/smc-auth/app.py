import uuid
import json

def lambda_handler(event, context):
    ret = {"id": str(uuid.uuid4())}

    return {
        "statusCode": 200,
        "body": json.dumps(ret)
    }