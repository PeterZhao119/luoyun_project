# -*- coding: utf-8 -*-
import os
import time

import sys
sys.path.append(".")

import xml.etree.ElementTree as ET
from connector.ecloud.ecloud_api import Ecloud_API

import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

from qiaoyun.tool.image import download_image
from framework.tool.voice2text.aliyun_asr import voice_to_text
from framework.tool.image2text.ark import ark_image2text

# {
#     "account": "17200000000",
#     "data": {
#         "content": "adfa",
#         "fromUser": "wxid_1dfgh4fs8vz22",
#         "msgId": 1052001123,
#         "newMsgId": 3166120021925175285,
#         "self": false,
#         "timestamp": 1640594470,
#         "toUser": "wxid_phyyedw9xap22",
#         "wId": "12491ae9-62aa-4f7a-83e6-9db4e9f28e3c"
#     },
#     "messageType": "60001",
#     "wcId": "wxid_phyyedw9xap22"
# }

# {
#     "_id": xxx,  # 内置id
#     "input_timestamp": xxx,  # 输入时的时间戳秒级
#     "handled_timestamp": xxx,  # 处理完毕时的时间戳秒级
#     "status": "pending",  # 标记处理状态：pending待处理，handled处理完毕，canceled不处理，failed处理失败
#     "from_user": "xxx",  # 来源uid
#     "platform": "xxx",  # 来源平台
#     "chatroom_name": None,  # 如果有值，则来自群聊；否则是私聊
#     "to_user": "xxx", # 目标用户；群聊时，值为None
#     "message_type": "xxxx",  # 包括：
#     "message": "xxx",  # 实际消息，格式另行约定
#     "metadata": {
#         "file_path": "xxx", # 所包含的文件路径
#     }
# }


def ecloud_message_to_std(message):
    if message["messageType"] in ["60001"]:
        return ecloud_message_to_std_text_single(message)
    if message["messageType"] in ["60002"]:
        return ecloud_message_to_std_image_single(message)
    if message["messageType"] in ["60014"]:
        return ecloud_message_to_std_reference_single(message)
    if message["messageType"] in ["60004"]:
        return ecloud_message_to_std_voice_single(message)

def ecloud_message_to_std_text_single(message):
    return {
        "input_timestamp": message["data"]["timestamp"],  # 输入时的时间戳秒级
        "handled_timestamp": None,  # 处理完毕时的时间戳秒级
        "status": "pending",  # 标记处理状态：pending待处理，handled处理完毕，canceled不处理，failed处理失败
        # "from_user": "xxx",  # 来源uid
        "platform": "wechat",  # 来源平台
        "chatroom_name": None,  # 如果有值，则来自群聊；否则是私聊
        # "to_user": "xxx", # 目标用户；群聊时，值为None
        "message_type": "text",  # 
        "message": message["data"]["content"],  # 实际消息，格式另行约定
        "metadata": {
        }
    }

def ecloud_message_to_std_reference_single(message):
    # {'wcId': 'wxid_7mww7784dgse22', 'data': {'toUser': 'wxid_7mww7784dgse22', 'msgType': 49, 'wId': 'ca9518dd-bec6-4421-b0f0-cbf81ecdb2f8', 'fromUser': 'LeanInWind', 'newMsgId': 6288973548168670026, 'msgId': 349799730, 'self': False, 'title': '好的', 'content': '<?xml version="1.0"?>\n<msg>\n\t<appmsg appid="" sdkver="0">\n\t\t<title>好的</title>\n\t\t<des />\n\t\t<action />\n\t\t<type>57</type>\n\t\t<showtype>0</showtype>\n\t\t<soundtype>0</soundtype>\n\t\t<mediatagname />\n\t\t<messageext />\n\t\t<messageaction />\n\t\t<content />\n\t\t<contentattr>0</contentattr>\n\t\t<url />\n\t\t<lowurl />\n\t\t<dataurl />\n\t\t<lowdataurl />\n\t\t<songalbumurl />\n\t\t<songlyric />\n\t\t<appattach>\n\t\t\t<totallen>0</totallen>\n\t\t\t<attachid />\n\t\t\t<emoticonmd5 />\n\t\t\t<fileext />\n\t\t\t<aeskey />\n\t\t</appattach>\n\t\t<extinfo />\n\t\t<sourceusername />\n\t\t<sourcedisplayname />\n\t\t<thumburl />\n\t\t<md5 />\n\t\t<statextstr />\n\t\t<refermsg>\n\t\t\t<type>1</type>\n\t\t\t<svrid>5893226576708700098</svrid>\n\t\t\t<fromusr>wxid_7mww7784dgse22</fromusr>\n\t\t\t<chatusr>LeanInWind</chatusr>\n\t\t\t<displayname>李洛云</displayname>\n\t\t\t<content>诶...我突然想到\n你说AI生成的完美图片不真实\n这其实跟心理咨询有点像呢\n来访者总想展现完美的自己\n但真正治愈的时刻往往发生在暴露脆弱的时候</content>\n\t\t\t<msgsource>&lt;msgsource&gt;\n\t&lt;bizflag&gt;0&lt;/bizflag&gt;\n\t&lt;pua&gt;1&lt;/pua&gt;\n\t&lt;signature&gt;N0_V1_43plNDgc|v1_uV3hKWDi&lt;/signature&gt;\n\t&lt;tmp_node&gt;\n\t\t&lt;publisher-id&gt;&lt;/publisher-id&gt;\n\t&lt;/tmp_node&gt;\n&lt;/msgsource&gt;\n</msgsource>\n\t\t\t<createtime>1748140474</createtime>\n\t\t</refermsg>\n\t</appmsg>\n\t<fromusername>LeanInWind</fromusername>\n\t<scene>0</scene>\n\t<appinfo>\n\t\t<version>1</version>\n\t\t<appname></appname>\n\t</appinfo>\n\t<commenturl></commenturl>\n</msg>\n', 'timestamp': 1748141489}, 'messageType': '60014', 'account': '15618861103'}
    metadata = {
        "reference": {
            "user": "未知",
            "text": ""
        }
    } # 组织引用消息
    content_xml = ET.fromstring(message["data"]["content"])

    user_nodes = content_xml.findall(f'.//displayname')
    for user_node in user_nodes:
        if user_node.text is not None:
            metadata["reference"]["user"] = user_node.text
    text_nodes = content_xml.findall(f'.//content')
    for text_node in text_nodes:
        if text_node.text is not None:
            metadata["reference"]["text"] = text_node.text

    return {
        "input_timestamp": message["data"]["timestamp"],  # 输入时的时间戳秒级
        "handled_timestamp": None,  # 处理完毕时的时间戳秒级
        "status": "pending",  # 标记处理状态：pending待处理，handled处理完毕，canceled不处理，failed处理失败
        # "from_user": "xxx",  # 来源uid
        "platform": "wechat",  # 来源平台
        "chatroom_name": None,  # 如果有值，则来自群聊；否则是私聊
        # "to_user": "xxx", # 目标用户；群聊时，值为None
        "message_type": "reference",  # 
        "message": message["data"]["title"],  # 实际消息，格式另行约定
        "metadata": metadata
    }

def ecloud_message_to_std_voice_single(message):
    resp_json = Ecloud_API.getMsgVoice({
        "wId": message["data"]["wId"],
        "msgId": message["data"]["msgId"],
        "fromUser": message["data"]["fromUser"],
        "bufId": message["data"]["bufId"],
        "length": message["data"]["length"]
    })

    voice_url = resp_json["data"]["url"]
    download_file_name = str(int(time.time()*1000)) + ".silk"
    file_path = download_image(voice_url, "luoyun/temp/", download_file_name)

    voice_text = voice_to_text(file_path)

    return {
        "input_timestamp": message["data"]["timestamp"],  # 输入时的时间戳秒级
        "handled_timestamp": None,  # 处理完毕时的时间戳秒级
        "status": "pending",  # 标记处理状态：pending待处理，handled处理完毕，canceled不处理，failed处理失败
        # "from_user": "xxx",  # 来源uid
        "platform": "wechat",  # 来源平台
        "chatroom_name": None,  # 如果有值，则来自群聊；否则是私聊
        # "to_user": "xxx", # 目标用户；群聊时，值为None
        "message_type": "voice",  # 
        "message": voice_text,  # 实际消息，格式另行约定
        "metadata": {
            "file_path": file_path,
            "voice_length": message["data"]["voiceLength"]
        }
    }

def ecloud_message_to_std_image_single(message):
    resp_json = Ecloud_API.getMsgImg({
        "wId": message["data"]["wId"],
        "msgId": message["data"]["msgId"],
        "content": message["data"]["content"]
    })
    logger.info(resp_json)
    image_url = resp_json["data"]["url"]
    image_text = ark_image2text("请详细描述图中有什么？输出不要分段和换行。", image_url)
    logger.info(image_text)

    m = {
        "input_timestamp": message["data"]["timestamp"],  # 输入时的时间戳秒级
        "handled_timestamp": None,  # 处理完毕时的时间戳秒级
        "status": "pending",  # 标记处理状态：pending待处理，handled处理完毕，canceled不处理，failed处理失败
        # "from_user": "xxx",  # 来源uid
        "platform": "wechat",  # 来源平台
        "chatroom_name": None,  # 如果有值，则来自群聊；否则是私聊
        # "to_user": "xxx", # 目标用户；群聊时，值为None
        "message_type": "image",  # 
        "message": image_text,  # 实际消息，格式另行约定
        "metadata": {
            "url": image_url,
        }
    }
    logger.info(m)
    return m

def std_to_ecloud_message(message):
    if message["message_type"] in ["text"]:
        return std_to_ecloud_message_text(message)
    if message["message_type"] in ["voice"]:
        return std_to_ecloud_message_voice(message)
    if message["message_type"] in ["image"]:
        return std_to_ecloud_message_image(message)
        
def std_to_ecloud_message_text(message):
    return {"content": message["message"]}

def std_to_ecloud_message_voice(message):
    return {
        "content": message["metadata"]["url"],
        "length": message["metadata"]["voice_length"]
    }

def std_to_ecloud_message_image(message):
    return {
        "content": message["metadata"]["url"]
    }



