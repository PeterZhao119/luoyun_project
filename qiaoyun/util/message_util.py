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

from util.time_util import timestamp2str
from dao.mongo import MongoDBBase
from dao.user_dao import UserDAO
from bson import ObjectId

def messages_to_str(messages, language="cn"):
    if len(messages) == 0:
        return ""
    
    messages_str_lines = []
    for message in messages:
        messages_str_lines.append(message_to_str(message, language))
    
    return "\n".join(messages_str_lines)

def message_to_str(message, language="cn"):
    try:
        if message["message_type"] in ["text", "voice"]:
            return normal_message_to_str(message, language=language)
        if message["message_type"] in ["reference"]:
            return reference_message_to_str(message, language=language)
        if message["message_type"] in ["image"]:
            return image_message_to_str(message, language=language)
    except Exception as e:
        logger.error(traceback.format_exc())
        return ""
    return ""

def normal_message_to_str(message, language="cn"):
    if "input_timestamp" in message:
        message_time = message["input_timestamp"]
    else:
        if message["expect_output_timestamp"] <= int(time.time()):
            message_time = message["expect_output_timestamp"]
        else:
            return "" # 如果expect_output_timestamp比now大，证明还没发出去

    user_dao = UserDAO()
    talker = user_dao.get_user_by_id(message["from_user"])
    talker_name = talker["platforms"][message["platform"]]["nickname"]
    time_str = timestamp2str(message_time)

    if language == "cn":
        message_type_map = {
            "text": "文本",
            "voice": "语音"
        }
        message_type_str = "文本"
        if message["message_type"] in message_type_map:
            message_type_str = message_type_map[message["message_type"]]

    return "（" + time_str + " " + talker_name + "发来了" + message_type_str + "消息）" + message["message"]

def reference_message_to_str(message, language="cn"):
    if "input_timestamp" in message:
        message_time = message["input_timestamp"]
    else:
        if message["expect_output_timestamp"] <= int(time.time()):
            message_time = message["expect_output_timestamp"]
        else:
            return "" # 如果expect_output_timestamp比now大，证明还没发出去

    user_dao = UserDAO()
    talker = user_dao.get_user_by_id(message["from_user"])
    talker_name = talker["platforms"][message["platform"]]["nickname"]
    time_str = timestamp2str(message_time)

    return "（" + time_str + " " + talker_name + "发来了一条引用消息）" + message["message"] + "「引用了" + message["metadata"]["reference"]["user"] + "的消息：" + message["metadata"]["reference"]["text"] + "」"

def image_message_to_str(message, language="cn"):
    if "input_timestamp" in message:
        message_time = message["input_timestamp"]
    else:
        if message["expect_output_timestamp"] <= int(time.time()):
            message_time = message["expect_output_timestamp"]
        else:
            return "" # 如果expect_output_timestamp比now大，证明还没发出去

    user_dao = UserDAO()
    talker = user_dao.get_user_by_id(message["from_user"])
    talker_name = talker["platforms"][message["platform"]]["nickname"]
    time_str = timestamp2str(message_time)

    mongo = MongoDBBase()
    image_str = ""

    if str(message["message"]).startswith(("「", "照片")) == True:
        image_id = str(message["message"]).replace("「", "")
        image_id = image_id.replace("」", "")
        image_id = image_id.replace("照片", "", 1)

        image = mongo.get_vector_by_id("embeddings", image_id)

        if image is not None:
            image_str = image["key"] + "：" + image["value"]

    return "（" + time_str + " " + talker_name + "发来了一条图片消息）" + message["message"] + "。" + image_str

# {
#     "_id": xxx,  # 内置id
#     "expect_output_timestamp": xxx,  # 预期输出的时间戳秒级
#     "handled_timestamp": xxx,  # 处理完毕时的时间戳秒级
#     "status": "pending",  # 标记处理状态：pending待处理，handled处理完毕，canceled不处理，failed处理失败
#     "from_user": "xxx",  # 来源uid
#     "platform": "xxx",  # 来源平台
#     "chatroom_name": None,  # 如果有值，则来自群聊；否则是私聊
#     "to_user": "xxx", # 目标用户uid；群聊时，值为None
#     "message_type": "xxxx",  # 包括：
#     "message": "xxx",  # 实际消息，格式另行约定
#     "metadata": {
#         "file_path": "xxx", # 所包含的文件路径
#     }
# }

def send_message_via_context(context, message, message_type="text", expect_output_timestamp=None, metadata={}):
    return send_message(
        platform=context["conversation"]["platform"],
        from_user=str(context["character"]["_id"]),
        to_user=str(context["user"]["_id"]),
        chatroom_name=context["conversation"]["chatroom_name"],
        message=message,
        message_type=message_type,
        status="pending",
        expect_output_timestamp=expect_output_timestamp,
        metadata=metadata
    )

def send_message(platform, from_user, to_user, chatroom_name, message, message_type="text", status="pending", expect_output_timestamp=None, metadata={}):
    mongo = MongoDBBase()
    now = int(time.time())
    if expect_output_timestamp is None:
        expect_output_timestamp = now

    outputmessage = {
        "expect_output_timestamp": expect_output_timestamp,  # 预期输出的时间戳秒级
        "handled_timestamp": expect_output_timestamp,  # 处理完毕时的时间戳秒级
        "status": status,  # 标记处理状态：pending待处理，handled处理完毕，canceled不处理，failed处理失败
        "from_user": from_user,  # 来源uid
        "platform": platform,  # 来源平台
        "chatroom_name": chatroom_name,  # 如果有值，则来自群聊；否则是私聊
        "to_user": to_user, # 目标用户uid；群聊时，值为None
        "message_type": message_type,  # 包括：
        "message": message,  # 实际消息，格式另行约定
        "metadata": metadata
    }

    mid = mongo.insert_one(
        "outputmessages",
        outputmessage
    )

    if mid is not None:
        outputmessage["_id"] = ObjectId(mid)
        return outputmessage
    else:
        return None