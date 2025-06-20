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

from framework.tool.text2voice.minimax import minimax_t2a
from util.file_util import pcm_to_silk
from util.oss import upload_file, bucket

def qiaoyun_voice_single(text, emotion=None):
    timber_weights = [
        {
        "voice_id": "Chinese (Mandarin)_IntellectualGirl",
        "weight": 40
        },
        {
        "voice_id": "Chinese (Mandarin)_Laid_BackGirl",
        "weight": 100
        }
    ]

    resp_json = minimax_t2a(text, timber_weights, emotion=emotion, speed=1.1, pitch=-1)
    hex = resp_json["data"]["audio"]
    decoded_hex = bytes.fromhex(hex)

    timestamp = str(int(time.time()*1000))
    file_path = "qiaoyun/temp/" + timestamp + ".pcm"
    with open(file_path, "wb") as f:
        f.write(decoded_hex)
    
    file_size = os.path.getsize(file_path)
    logger.info("file_size: " + str(file_size))
    voice_length = int(file_size/1000/50) * 1000

    new_file_path = pcm_to_silk(file_path)

    with open(new_file_path, "rb") as f:
        data = f.read()
    upload_file(bucket, timestamp + ".silk", data)

    url = bucket.sign_url("GET", timestamp + ".silk", 60*60)
    
    return url, voice_length

def qiaoyun_voice(text, emotion=None):
    emotion_map = {
        "高兴": "happy",
        "悲伤": "sad",
        "愤怒": "angry",
        "害怕": "fearful",
        "惊讶": "surprised",
        "厌恶": "disgusted",
        "魅惑": "fearful"
    }

    if emotion not in emotion_map:
        emotion = None
    else:
        emotion = emotion_map[emotion]

    results = []
    text = text.replace("<换行>", "")
    texts = split_string(text)
    for text in texts:
        url, voice_length = qiaoyun_voice_single(text, emotion)
        results.append((url, voice_length))
        logger.info("voice url:" + url)
        logger.info("voice length:" + str(voice_length))

    return results

def split_string(text, chunk_size=420):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    # resp_json = Ecloud_API.sendVoice(data={
    #     "wId": CONF["ecloud"]["wId"][target_user_alias],
    #     "wcId": "LeanInWind",
    #     "content": url,
    #     "length": voice_length
    # })

    # print(resp_json)
