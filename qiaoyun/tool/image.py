import sys
sys.path.append(".")
import copy
import os
import time
import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

import requests
from urllib.parse import urlparse

from framework.tool.text2image.liblib import text2img, getstatus
from util.oss import upload_file, bucket

def generate_qiaoyun_image(prompt, imgCount=1, mode=0, sub_mode="半身照", resizedWidth=768, resizedHeight=1024):
    char_lora_info = "bursty breasts, miluo_zg,"
    char_head = "(only one Asian girl),age 26, long black hair,straight hairstyle,elegant oval face,porcelain white skin,sharp phoenix eyes,thin arched eyebrows,high nose bridge,small cherry lips,defined jawline,subtle gray eyeshadow,nice fingers, nice hands,"

    # char_breasts = "(super huge breasts:1.4), "
    # char_lower = "thin waist, a little fat butt,"

    char_breasts = ","
    char_lower = ","

    additionalNetwork = []
    if mode == 0: # 人物照
        checkPointId = "104c076149f14a3a8f0ac148ce780e87" # 亚洲女性_细节摄影_f8
        prompt = char_lora_info + prompt
        prompt = char_head + prompt
        additionalNetwork =  [
            {
                "modelId": "b9171e4a85e44d61a56de4a16e820879", # 麦橘超美 majicFlus
                "weight": 0.4
            },
            {
                "modelId": "37226fda3dbc4285b75e0e414adae592", # F.1CG-古风玄幻唯美人像
                "weight": 0.8
            },
            {
                "modelId": "8d01e6b9ba734126a945c11749fd8506", # Flux_小马-完美全圆胸纤腰
                "weight": 0.55
            },
            {
                "modelId": "d66f79440e854f94b6b3f64e44a32e0a", # Flux丨肌肤质感调节器_毛孔细节，真实人像
                "weight": 0.2
            }
        ]
    else:
        checkPointId = "412b427ddb674b4dbab9e5abd5ae6057" # 静物
        additionalNetwork = []
    
    if sub_mode in ["全身照", "半身照"]:
        prompt = char_breasts + prompt
    
    if sub_mode in ["全身照"]:
        prompt = char_lower + prompt

    prompt = "no logo," + prompt

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
        "width": resizedWidth,
        "height": resizedHeight,  

        # "mode": 4,
        # "denoisingStrength": 0.75, // 重绘幅度
        
        # Lora添加，最多5个
        "additionalNetwork": additionalNetwork
    }

    resp_json = text2img(generateParams)
    logger.info(resp_json)

    generateUuid = resp_json["data"]["generateUuid"]
    return generateUuid

def generate_qiaoyun_image_save(generateUuid, save_path="qiaoyun/role/qiaoyun/role_image/"):
    # task_id = "70655e501358462d871adb4c4e771d8f"
    for i in range(60):
        time.sleep(5)      
        status_json = getstatus(generateUuid)
        logger.info(status_json)

        if status_json["data"]["generateStatus"] >= 5:
            saved_paths = []
            origin_paths = []
            for image in status_json["data"]["images"]:
                file_name = str(image["imageUrl"]).split("/")[-1]
                saved_path = download_image(image["imageUrl"], save_path, file_name)
                origin_paths.append(image["imageUrl"])
                saved_paths.append(saved_path)
            return origin_paths, saved_paths

def download_image(url, save_path=None, filename=None, timeout=10):
    """
    下载公网图片到本地（支持自定义文件名）
    :param url: 图片公网地址（需带http/https）
    :param save_path: 保存路径（可以是完整路径或目录路径）
    :param filename: 自定义文件名（带扩展名）
    :param timeout: 请求超时时间（秒）
    :return: 文件保存路径
    """
    try:
        response = requests.get(url, 
                              stream=True,
                              timeout=timeout,
                              headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()

        # 构建保存路径逻辑
        if filename:  # 优先使用自定义文件名
            if save_path:
                # 提取原始路径的目录部分
                save_dir = os.path.dirname(save_path)
                # 处理纯目录路径（如以/结尾的路径）
                if not os.path.basename(save_path):
                    save_dir = save_path.rstrip(os.sep)
            else:
                save_dir = os.getcwd()
            
            # 合成最终路径
            save_path = os.path.join(save_dir, filename)
        elif not save_path:  # 自动生成文件名
            path = urlparse(url).path
            auto_name = os.path.basename(path) or 'downloaded_image.jpg'
            save_path = os.path.join(os.getcwd(), auto_name)

        # 创建目录（如果不存在）
        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)

        # 写入文件
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        logger.info(f"文件已保存至：{os.path.abspath(save_path)}")
        return save_path
    
    except Exception as e:
        logger.info(f"下载失败：{str(e)}")
        return None

def upload_image(photo_id):
    from dao.mongo import MongoDBBase

    mongo = MongoDBBase()

    photo = mongo.get_vector_by_id("embeddings", photo_id)
    if photo is None:
        return None
    
    local_path = photo["metadata"]["file"]
    with open(local_path, "rb") as f:
        data = f.read()
    file_name = local_path.split("/")[-1]
    upload_file(bucket, file_name, data)

    url = bucket.sign_url("GET", file_name, 60*60)
    
    return url

# 启动脚本
if __name__ == "__main__":
    prompt = '''one girl'''

    task_id = generate_qiaoyun_image(prompt, 1, 0, "全身照")
    saved = generate_qiaoyun_image_save(task_id)
    print(saved)
    
