import hmac
from hashlib import sha1
import base64
import time
import uuid
import requests
import sys
sys.path.append(".")

from conf.config import CONF
from util.str_util import remove_chinese

host = "https://openapi.liblibai.cloud"

def make_sign(uri="/api/generate/webui/text2img"):
    """
    生成签名
    """
    # host = "https://openapi.liblibai.cloud"

    # API访问密钥
    access_key = CONF["liblib"]["AccessKey"]
    secret_key = CONF["liblib"]["SecretKey"]

    # 请求API接口的uri地址
    # uri = "/api/generate/webui/text2img"
    # 当前毫秒时间戳
    timestamp = str(int(time.time() * 1000))
    # 随机字符串
    signature_nonce= str(uuid.uuid4())
    # 拼接请求数据
    content = '&'.join((uri, timestamp, signature_nonce))
    
    # 生成签名
    digest = hmac.new(secret_key.encode(), content.encode(), sha1).digest()
    # 移除为了补全base64位数而填充的尾部等号
    sign = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()

    uri_params = [
        "AccessKey=" + access_key,
        "Signature=" + sign,
        "Timestamp=" + timestamp,
        "SignatureNonce=" + signature_nonce
    ]
    uri_param = '&'.join(uri_params)

    return uri_param

# https://openapi.liblibai.cloud
# https://test.xxx.com/api/genImg?AccessKey=KIQMFXjHaobx7wqo9XvYKA&Signature=test1232132&Timestamp=1725458584000&SignatureNonce=random1232

def text2img(generateParams, templateUuid="6f7c4652458d4802969f8d089cf5b91f"):
    uri = "/api/generate/webui/text2img"
    uri_param = make_sign(uri)

    resp = requests.post(
        url = host + uri + "?" + uri_param,
        headers={"Content-Type": "application/json"},
        json={
            "templateUuid": templateUuid,
            "generateParams": generateParams
        }
    )

    resp_json = resp.json()
    return resp_json

def getstatus(generateUuid):
    uri = "/api/generate/webui/status"
    uri_param = make_sign(uri)

    resp = requests.post(
        url = host + uri + "?" + uri_param,
        headers={"Content-Type": "application/json"},
        json={
            "generateUuid": generateUuid
        }
    )

    resp_json = resp.json()
    return resp_json

# 启动脚本
if __name__ == "__main__":
    def generate_one_luoyun(prompt, imgCount=1, mode=0, sub_mode="半身照", resizedWidth=768, resizedHeight=1024):
        char_lora_info = "bursty breasts, FRESHIDEAS Perfect lady's fingers, miluo_zg,"
        char_head = "(only one Asian girl),age 24,brown hair,small wave hairstyle,long hair on shoulder,shawl hair,(porcelain-dewy skin, almond-shaped double eyelids, large eyes with slightly upturned outer corners, silky raven-black hair, short nose, short face, little round jaw, round chin, nude color lips),nice fingers, nice hands,"

        char_breasts = "(super huge breasts under clothes:1.4), "
        char_lower = "thin waist, a little fat butt,"   

        if mode == 0: # 人物照
            checkPointId = "eb80645cc47a4a65940a105a7daf5632" # 麦橘
            prompt = char_lora_info + prompt
            prompt = char_head + prompt
            additionalNetwork =  [
                {
                    "modelId": "b9171e4a85e44d61a56de4a16e820879", # 麦橘超美 majicFlus
                    "weight": 0.4
                },
                {
                    "modelId": "8ae3c0cdc36740a0953bd8e5cb5d8bcd", # 星梦·街拍模型_亚洲人像·街拍
                    "weight": 0.6
                },
                {
                    "modelId": "8d01e6b9ba734126a945c11749fd8506", # Flux_小马-完美全圆胸纤腰
                    "weight": 0.4
                },
                {
                    "modelId": "d66f79440e854f94b6b3f64e44a32e0a", # Flux丨肌肤质感调节器_毛孔细节，真实人像
                    "weight": 0.2
                },
                {
                    "modelId": "f8cdb49d52644876a14bfd6109e4332f", # 鲜创一派@F.1-女人手部优化修复
                    "weight": 0.6
                }
            ],
        else:
            checkPointId = "412b427ddb674b4dbab9e5abd5ae6057" # 静物
            additionalNetwork = []
        
        if sub_mode in ["全身照", "半身照"]:
            prompt = char_breasts + prompt
        
        if sub_mode in ["全身照"]:
            prompt = char_lower + prompt

        prompt = "no logo," + prompt

        prompt = remove_chinese(prompt)

        generateParams = {
            # 基础参数
            "checkPointId": checkPointId, 
            "prompt": prompt,
            "negativePrompt": "ng_deepnegative_v1_75t,(badhandv4:1.2),EasyNegative,(worst quality:2),",
            "clipSkip": 2,
            "sampler": 1, # Euler
            "steps": 25,
            "cfgScale": 3.5,
            "randnSource": 0,
            "seed": -1,
            "imgCount": imgCount,
            "restoreFaces": 0,  
            # 图像相关参数
            # "sourceImage": "https://liblibai-online.liblib.cloud/img/081e9f07d9bd4c2ba090efde163518f9/7c1cc38e-522c-43fe-aca9-07d5420d743e.png",
            "resizeMode": 0,
            "resizedWidth": resizedWidth, 
            "resizedHeight": resizedHeight,
            # "mode": 4,
            # "denoisingStrength": 0.75, // 重绘幅度
            
            # Lora添加，最多5个
            "additionalNetwork": additionalNetwork
        }

        resp_json = text2img(generateParams)
        print(resp_json)

        generateUuid = resp_json["data"]["generateUuid"]
        return generateUuid

    prompt = '''wearing a thin strap nightgown,action is casually standing in front of the mirror,scene is a hotel room,standing in front of a full-length mirror,slightly motion blurred due to insufficient shutter speed,composition is casual,angle is awkward,the image is not symmetrical or aesthetically pleasing,the quality has a sense of everydayness and roughness,conveys "plain and unremarkable.", nice fingers,nice body,nice hands,nice legs,no fused fingers,
(only one Asian girl),age 24,brown hair,small wave hairstyle,long hair on shoulder,shawl hair,(super huge breasts under upper clothes:1.4),(cleavage),
(full body shot, side shot, side face),
(Porcelain-dewy skin, almond-shaped double eyelids, large eyes with slightly upturned outer corners, silky raven-black hair, short nose, short face, little round jaw, round chin),no logo, no tatoo, '''

    task_id = generate_one_luoyun(prompt, 2)
    print(task_id)

    # task_id = "70655e501358462d871adb4c4e771d8f"
    for i in range(60):
        time.sleep(5)      
        status_json = getstatus(task_id)
        print(status_json)

        if status_json["data"]["generateStatus"] >= 5:
            break