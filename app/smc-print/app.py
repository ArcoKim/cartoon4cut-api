import boto3
import botocore
import cv2
import numpy as np
import uuid
import qrcode
import os
import json

s3 = boto3.client("s3")

bucket = os.getenv("BUCKET_NAME")
ids = str(uuid.uuid1())
checks = ["disney", "clay", "flat2d", "real3d", "comics"]
frame_map = {
    "카툰네컷 기본 프레임 - 화이트": "white",
    "카툰네컷 기본 프레임 - 세명인이되": "smc",
    "카툰네컷 기본 프레임 - 핑크": "pink",
    "카툰네컷 기본 프레임 - 금지구역": "ban",
    "카툰네컷 기본 프레임 - 종이": "paper"
}

def get_filter(file):
    for check in checks:
        key = f"transformed/{check}/{file}"
        try:
            s3.head_object(Bucket=bucket, Key=key)
            return check
        except botocore.exceptions.ClientError as e:
            pass

def apply_filter(file, size):
    filt = get_filter(file)
    og = get_image(f"origin/{filt}/{file}")
    og = cv2.resize(og, size)
    tf = get_image(f"transformed/{filt}/{file}")
    tf = cv2.resize(tf, size)
    return og, tf

def get_image(key, tp=False):
    obj = s3.get_object(Bucket=bucket, Key=key)
    np_arr = np.frombuffer(obj['Body'].read(), np.uint8)
    color = cv2.IMREAD_UNCHANGED if tp else cv2.IMREAD_COLOR
    return cv2.imdecode(np_arr, color)

def get_parts(background, key, pos, size=False):
    part = get_image(key, True)
    if size:
        part = cv2.resize(part, size)
    p_h, p_w = part.shape[:2]
    
    mask = part[:,:,3]
    c_p = part[:,:,:3]
    crop = background[pos[0]:pos[0]+p_h, pos[1]:pos[1]+p_w]
    cv2.copyTo(c_p, mask, crop)
    
    return background

def preview(image, frame):
    frame_id = frame_map[frame]
    rect = get_image(f"frame/background/{frame_id}.png")[:1194, :]
    rect = cv2.resize(rect, (690, 824))
    bg_h, bg_w = rect.shape[:2]
    
    if frame_id == "smc":
        rect = get_parts(rect, f"frame/top/{frame_id}.png", (62, 32), (302, 60))
        rect = get_parts(rect, f"frame/bottom/{frame_id}.png", (bg_h-172, bg_w-244), (140, 160))
    elif frame_id == "ban":
        rect = get_parts(rect, f"frame/bottom/{frame_id}.png", (bg_h-142, bg_w-334), (302, 110))
    else:
        rect = get_parts(rect, f"frame/top/{frame_id}.png", (40, 32), (302, 82))
        rect = get_parts(rect, f"frame/bottom/{frame_id}.png", (bg_h-130, bg_w-334), (302, 88))

    o1, t1 = apply_filter(image[0], (302, 302))
    o2, t2 = apply_filter(image[1], (302, 302))
    o_h, o_w = o1.shape[:2]

    rect[164:164+o_h, 32:32+o_w] = o1
    rect[490:490+o_h, 32:32+o_w] = o2
    rect[32:32+o_h, bg_w-o_w-32:bg_w-32] = t1
    rect[358:358+o_h, bg_w-o_w-32:bg_w-32] = t2

    image_string = cv2.imencode(".png", rect)[1].tostring()
    key = f"print/preview/{ids}.png"
    s3.put_object(Bucket=bucket, Key=key, Body=image_string, ContentType="image/png")

    return f"https://{bucket}.s3.ap-northeast-2.amazonaws.com/{key}"

def result(image, frame):
    frame_id = frame_map[frame]
    background = get_image(f"frame/background/{frame_id}.png")

    if frame_id == "ban":
        background = get_parts(background, f"frame/bottom/{frame_id}.png", (1152, 395))
    elif frame_id == "smc":
        background = get_parts(background, f"frame/top/{frame_id}.png", (240, 105))
        background = get_parts(background, f"frame/bottom/{frame_id}.png", (1100, 580))
    else:
        background = get_parts(background, f"frame/top/{frame_id}.png", (80, 80))
        background = get_parts(background, f"frame/bottom/{frame_id}.png", (1175, 278))

    o1, t1 = apply_filter(image[0], (400, 400))
    o2, t2 = apply_filter(image[1], (400, 400))
    o_h, o_w = o1.shape[:2]

    if frame_id == "ban":
        background[290:290+o_h, 80:80+o_w] = o1
        background[730:730+o_h, 80:80+o_w] = o2
    else:
        background[330:330+o_h, 80:80+o_w] = o1
        background[770:770+o_h, 80:80+o_w] = o2
    background[260:260+o_h, 520:520+o_w] = t1
    background[700:700+o_h, 520:520+o_w] = t2

    if frame_id not in ("ban", "smc"):
        background = get_parts(background, f"frame/decoration/{frame_id}.png", (175, 19))

    key = f"print/result/{ids}.png"
    link = f"https://{bucket}.s3.ap-northeast-2.amazonaws.com/{key}"
    qrloc = "/tmp/qrc.png"

    qrc = qrcode.make(link)
    qrc.save(qrloc)
    qrcv = cv2.imread(qrloc)
    qrcv = cv2.resize(qrcv, (150, 150))
    background[80:230, 770:920] = qrcv
    
    image_string = cv2.imencode(".png", background)[1].tostring()
    s3.put_object(Bucket=bucket, Key=key, Body=image_string, ContentType="image/png")

    return link

def lambda_handler(event, context):
    body = json.loads(event["body"])

    ret = {
        "preview": preview(body["image"], body["frame"]),
        "result": result(body["image"], body["frame"])
    }

    return {
        "statusCode": 200,
        "body": json.dumps(ret)
    }