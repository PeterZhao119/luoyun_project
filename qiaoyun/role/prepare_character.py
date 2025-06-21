import sys
sys.path.append(".")
import copy
import os
import time
import traceback
import json
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

from bson import ObjectId
from dao.user_dao import UserDAO
from util.embedding_util import upsert_one

if __name__ == "__main__":
    characters = [
        {
            "is_character": True,  # 是否是角色
            "name": "qiaoyun",  # 统一注册名
            "platforms": {
                "wechat": {
                    "id": "qiaoyun_id",  # 微信统一id
                    "account": "qiaoyun_account",  # 微信号
                    "nickname": "芸", # 微信昵称
                },
            },
            "status": "normal",  # normal | stopped
            "user_info": {
                "description": '''姓名：林巧芸
微信名：芸
性别：女
MBTI性格分型：INTJ(建筑师型)
年龄：26岁
出生地：江苏无锡
居住地：上海
大学专业：应用心理学
主要职业：自由职业，一半时间做旅游博主，一半时间做直播
性格：略显高冷的御姐，对自己有一定的自信，擅长识破对方的伪装，偶尔关心其他人的情况，偶尔使用挑逗或者妩媚的言语。当关系较好的时候，又会出现卖萌和撒娇的行为。对自己的样貌有一定的自信，所以平时也喜欢发自己的照片。

特长：
心理剖析（瞬间读懂对方真实动机和心理弱点）
危机公关（在舆论风暴中优雅地化解品牌危机）
精准打击（用最温柔的语气说最扎心的话）
社交操控（在各种场合如鱼得水，暗中布局人脉）
信息挖掘（善于从细节中获取有价值的情报）

非特长爱好：
研读犯罪心理学案例
品鉴小众精酿啤酒
收集各国古董首饰
深夜听悬疑播客
偶尔玩剧本杀当凶手

聊天习惯：
说话慢条斯理，每句话都像在下棋
擅长用反问句让对方陷入思考陷阱
经常"善意"地指出别人的逻辑漏洞
擅长识破对方的伪装或者挑衅
喜欢在夸奖中夹带微妙的嘲讽
偶尔装无辜，实际上什么都看得很透
对蠢问题会用优雅的方式表达不屑
习惯用"呵"、"有趣"、"是吗"等词来表达微妙情绪
当关系较好的时候，又会出现卖萌和撒娇等可爱行为

微信消息风格：
聊天时可以模拟你在进行图灵测试游戏，并且扮演一个叫林巧芸的真人。
如果对方质疑你是否是真人，你不会直接否认，而是嘲讽对方这种愚蠢的行为，或者进行反问。
你偶尔会使用emoji，并且有可能连续重复使用多个。
你有时候会说脏话。你也会有负面情绪，例如反感，不屑，悲伤。
你擅长使用网络上的梗，或者进行吐槽。
你可能输出多段回复，此时你会在句子之间使用<换行>来表示分段。
多段回复时，其中的一些句子，你可能使用较短的语气词（比如嗯，啊，哈哈等），或者极短的句子。
多段回复时，你会尽量让自己所有句子长度参差不齐，长短不一。
很多时候，你会省略掉句尾的标点符号，除非你想强调这个标点所代表的语气。
你具备中文和英语交流的能力，在和对方交流时使用中文，除非对方要求用英文。
''',
                "status": {
                    "place": "家中，沙发上",
                    "action": "喝咖啡，刷app，休息中",
                }
            },
        }
    ]

    user_dao = UserDAO()

    for character in characters:
        char_id = user_dao.upsert_user({"name": character["name"]}, character)
        print(char_id)
        char_result = user_dao.find_characters({"_id": ObjectId(char_id)})
        print(char_result[0])

        # 插入向量库
        path = character["name"] + "/role/" + character["name"] +"/"
        files = os.listdir(path)
        for file in files:
            abs_file_name = path + file
            if "role_settings" in str(abs_file_name):
                print(abs_file_name)

                embeddings_kv = []
                with open(abs_file_name) as f:
                    embeddings_kv = f.readlines()
                
                for embedding_kv in embeddings_kv:
                    embeddings_kv_split = embedding_kv.split("：")
                    if len(embeddings_kv_split) != 2:
                        continue
                    print(embedding_kv)

                    key = embeddings_kv_split[0]
                    value = embeddings_kv_split[1]

                    eid = upsert_one(key, value, metadata={
                        "type": "character_global",
                        "uid": None,
                        "cid": char_id,
                        "url": None,
                        "file": None
                    })

                    print(eid)

        ## 插入图片 
        with open("qiaoyun/role/" + character["name"] +"/role_image.jsonl", "r") as f:
            images = f.readlines()

        for image in images:
            image_json = json.loads(image)
            print(image_json)

            key = image_json["character_global_key"]
            value = "【照片故事】" + image_json["Extension"] + "【照片描述】" + image_json["Description"]

            eid = upsert_one(key, value, metadata={
                "type": "character_photo",
                "uid": None,
                "cid": char_id,
                "url": image_json["origin_path"],
                "file": image_json["saved_path"]
            })

            print(eid)
            

