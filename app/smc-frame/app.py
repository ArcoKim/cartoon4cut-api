import boto3
import os
import json

s3 = boto3.client('s3')
objs = {
    "white": {
        "name": "카툰네컷 기본 프레임 - 화이트",
        "pos": ["top", "background", "bottom"]
    },
    "smc": {
        "name": "카툰네컷 기본 프레임 - 세명인이되",
        "pos": ["top", "background", "bottom"]
    },
    "pink": {
        "name": "카툰네컷 기본 프레임 - 핑크",
        "pos": ["top", "background", "bottom"]
    },
    "ban": {
        "name": "카툰네컷 기본 프레임 - 금지구역",
        "pos": ["background", "bottom"]
    },
    "paper": {
        "name": "카툰네컷 기본 프레임 - 종이",
        "pos": ["top", "background", "bottom"]
    }
}
poss = ["top", "background", "bottom"]
bucket = os.getenv("BUCKET_NAME")

def lambda_handler(event, context):
    ret = []
    
    for obj in objs:
        now = {}
        for pos in poss:
            now[pos] = None
            if pos in objs[obj]["pos"]:
                now[pos] = f"https://{bucket}.s3.ap-northeast-2.amazonaws.com/frame/{pos}/{obj}.png"
        now["name"] = objs[obj]["name"]
        ret.append(now)
    
    return {
        "statusCode": 200,
        "body": json.dumps(ret)
    }