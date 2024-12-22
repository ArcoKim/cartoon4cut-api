import asyncio
import aioboto3
import aiohttp
import boto3
import os
import uuid
import io
import json
import base64
from PIL import Image
from requests_toolbelt.multipart import decoder

session = aioboto3.Session()
ec2 = boto3.client('ec2')
bucket = os.getenv("BUCKET_NAME")

async def upload(image, key, s3):
    with io.BytesIO() as img_bytes:
        image.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        await s3.put_object(Bucket=bucket, Key=key, Body=img_bytes, ContentType='image/png')

async def img2img(part, filt, s3):
    print(filt + " transform start")
    
    instance = ec2.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [filt]
            }
        ]
    )
    url = f'http://{instance['Reservations'][0]['Instances'][0]['PublicIpAddress']}:8080'
    filename = str(uuid.uuid1()) + ".png"
    
    # Prompt
    if filt == "flat2d":
        p_env = "(best quality:0.8), (boy:0.5), perfect anime portrait illustration, front forward, (masterpiece:1.5), high quality, best quality, 32k, (best-quality:0.8), perfect anime illustration, person, teen"
        n_p_mod = "(worst quality:0.8),verybadimagenegative_v1.3,(surreal:0.8), (modernism:0.8), (art deco:0.8), (art nouveau:0.8), low quality, nsfw, nude, verybadimagenegative_v1.3, (surreal:0.8), (modernism:0.8), (art deco:0.8), (art nouveau:0.8), watermark, makeup"
    elif filt == "real3d":
        p_env = "(masterpiece:1.5), high quality, best quality, (best quality:0.8), front forward, 32k, person, teen"
        n_p_mod = "nsfw, nude, easynegative,(badhandv4),(bad quality:1.3),(worst quality:1.3),watermark,(blurry),5-funny-looking-fingers, worst quality, low quality, nude, watermark, makeup"
    elif filt == "disney":
        p_env = "detailed eyes,(((masterpiece))),(((best quality))), ((ultra-detailed)), (highly detailed CG illustration), high quality, best quality, 32k, person, teen"
        n_p_mod = "easynegative, bad-artist, bad-artist-anime, nsfw, nude, 19, (bad_prompt:0.8), (artist name, signature, watermark:1.4), (ugly:1.2), (worst quality, poor details:1.4), bad-hands-5, badhandv4, blurry,child"
    elif filt == "comics":
        p_env = "(best quality:0.8), man, (boy:0.5), perfect anime portrait illustration, front forward, (masterpiece:1.5), high quality, best quality, 32k,backlighting, teen"
        n_p_mod = "easynegative, woman, girl, female, bad-artist, bad-artist-anime, nsfw, nude, 19, (bad_prompt:0.8), (artist name, signature, watermark:1.4), (ugly:1.2), (worst quality, poor details:1.4), bad-hands-5, badhandv4, blurry,child"
    elif filt == "clay": #real3d
        p_env = "claymation, clay art, <lora:CLAYMATE_V2.03_:1>, young, teen, (masterpiece:1.5), high quality, best quality, (best quality:0.8), front forward, 32k,person, teen"
        n_p_mod = "nsfw, nude, easynegative,wrinkles(badhandv4),(bad quality:1.3),(worst quality:1.3),watermark,(blurry),5-funny-looking-fingers, worst quality, low quality, nude, watermark, makeup"
    else:
        return

    image = Image.open(io.BytesIO(part.content))
    width, height = image.size
    await upload(image, f'origin/{filt}/{filename}', s3)
    print(filt + " origin upload complete!")

    img_base64 = base64.b64encode(part.content).decode('utf-8')
    img2img_payload = {
        "init_images": [img_base64],
        "prompt": p_env,
        "negative_prompt": n_p_mod,
        "denoising_strength": 0.5,
        "width": width,
        "height": height,
        "cfg_scale": 7,
        "sampler_name": "DPM++ 3M SDE",
        "scheduler": "Karras",
        "restore_faces": False,
        "steps": 30,
        "override_settings": {
            "CLIP_stop_at_last_layers": 2
        },
        "override_settings_restore_afterwards": False
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url=f'{url}/sdapi/v1/img2img', json=img2img_payload) as response:
            r = await response.json()
    print(filt + " img2img complete!")

    image_data = base64.b64decode(r['images'][-1].split(",", 1)[0])
    image = Image.open(io.BytesIO(image_data))
    await upload(image, f'transformed/{filt}/{filename}', s3)
    print(filt + " transform  complete!")
        
    print(filt + " transform end")
    return filename

async def main(event):
    headers = event['headers']
    content_type_header = headers.get('content-type', headers.get('Content-Type'))
    postdata = base64.b64decode(event['body'])
    types = headers['type'].split('/')

    async with session.client('s3') as s3:
        parts = decoder.MultipartDecoder(postdata, content_type_header).parts
        tasks = [img2img(parts[idx], types[idx], s3) for idx in range(2)]
        ret = await asyncio.gather(*tasks)
    
    return {
        "statusCode": 200,
        "body": json.dumps(ret)
    }
    
def lambda_handler(event, context):
    return asyncio.run(main(event))