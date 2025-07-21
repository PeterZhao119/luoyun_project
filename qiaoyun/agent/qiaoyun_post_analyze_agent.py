# -*- coding: utf-8 -*-
import os
import time

import sys
sys.path.append(".")

import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

from framework.agent.base_agent import AgentStatus
from framework.agent.llmagent.doubao_llmagent import DouBaoLLMAgent
from conf.config import CONF
from volcenginesdkarkruntime import Ark

from dao.mongo import MongoDBBase
from util.embedding_util import upsert_one

from qiaoyun.prompt.system_prompt import *
from qiaoyun.prompt.chat_taskprompt import *
from qiaoyun.prompt.chat_contextprompt import *
from qiaoyun.prompt.chat_noticeprompt import *

doubao_client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

# 需要 export ARK_API_KEY="xxxx"
class QiaoyunPostAnalyzeAgent(DouBaoLLMAgent):
    default_systemp_template = SYSTEMPROMPT_小说越狱

    default_userp_template = \
    "## 你的任务" + "\n" + \
    TASKPROMPT_小说书写任务 + "\n" + \
    "\n" + \
    TASKPROMPT_总结 + "\n" + \
    TASKPROMPT_总结_推理要求 + "\n" + \
    "\n" + \
    "## 参考上下文" + "\n" + \
    CONTEXTPROMPT_时间 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物信息 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物资料 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_用户资料 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物知识和技能 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物状态 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_当前目标 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_当前的人物关系 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_历史对话 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_最新聊天消息_双方

    default_output_schema = {
        "type": "object",
        "properties": {
            "InnerMonologue": {
                "type": "string",
                "description": "角色的内心独白"
            },
            "CharacterPublicSettings": {
                "type": "string",
                "description": "总结最新聊天消息中，针对角色所新增的人物设定。你可以总结出1条或者多条信息，每条消息为一行；使用'key：value'的形式，例如 xxx-xxx-xxx：xxxxxx。"
            },
            "CharacterPrivateSettings": {
                "type": "string",
                "description": "总结最新聊天消息中，针对角色所新增的不可公开人物设定。你可以总结出1条或者多条信息，每条消息为一行；使用'key：value'的形式，例如 xxx-xxx-xxx：xxxxxx。"
            },
            "CharacterKnowledges": {
                "type": "string",
                "description": "总结最新聊天消息中，角色所新增的知识或技能点。你可以总结出1条或者多条信息，每条消息为一行；使用'key：value'的形式，例如 xxx-xxx-xxx：xxxxxx。"
            },
            "UserSettings": {
                "type": "string",
                "description": "总结最新聊天消息中，针对用户所新增的人物设定。你可以总结出1条或者多条信息，每条消息为一行；使用'key：value'的形式，例如 xxx-xxx-xxx：xxxxxx。"
            },
            "UserRealName": {
                "type": "string",
                "description": "总结最新聊天消息中，角色所了解到的用户的真名。如果没有，你需要输出”无“。"
            },
            "UserHobbyName": {
                "type": "string",
                "description": "总结最新聊天消息中，双方约定的给用户的亲密昵称。如果没有，你需要输出”无“。"
            },
            "UserDescription": {
                "type": "string",
                "description": "总结最新聊天消息中，角色对用户的印象描述。你需要结合”参考上下文“中的印象描述，进行更新。最多不超过100字。"
            },
            "CharacterPurpose": {
                "type": "string",
                "description": "总结最新聊天消息中，角色的短期目标，可能跟多轮聊天有关，也可能无关。可以涉及一些隐式的长线心理活动，例如故意卖关子，故意激怒，假装欺骗等等。"
            },
            "CharacterAttitude": {
                "type": "string",
                "description": "总结最新聊天消息中，角色对用户的态度。"
            },
            "RelationDescription": {
                "type": "string",
                "description": "总结最新聊天消息中，角色和用户的关系变化。如果没有变化，你应该输出原关系。"
            },
            "Dislike": {
                "type": "integer",
                "description": "总结最新聊天消息中，角色对用户的的反感度数值变化。如果更加反感了，应该输出正整数。"
            },
        }
    }

    def __init__(self, context=None, client=doubao_client, systemp_template=default_systemp_template, userp_template=default_userp_template, output_schema=default_output_schema, default_input=None, max_retries=3, name=None, stream=False, model="doubao_1.5_pro", extra_args=None):
        super().__init__(context, client, systemp_template, userp_template, output_schema, default_input, max_retries, name, stream, model, extra_args)

    def _posthandle(self):
        def upsert_vector(kv_str, embedding_type):
            splits = kv_str.split("：")
            if len(splits) < 2:
                return None
            
            key = splits[0]
            value = splits[1]

            char_id = str(self.context["character"]["_id"])

            metadata = {
                "type": embedding_type,
                "cid": char_id,
                "url": None,
                "file": None
            }

            if embedding_type in ["character_private", "user"]:
                metadata["uid"] = str(self.context["user"]["_id"])

            return upsert_one(key, value, metadata)
        
        if self.resp["CharacterPublicSettings"] != "无":
            splits = self.resp["CharacterPublicSettings"].split("<换行>")
            for split in splits:
                upsert_vector(split, "character_global")
        if self.resp["CharacterPrivateSettings"] != "无":
            splits = self.resp["CharacterPrivateSettings"].split("<换行>")
            for split in splits:
                upsert_vector(split, "character_private")
        if self.resp["CharacterKnowledges"] != "无":
            splits = self.resp["CharacterKnowledges"].split("<换行>")
            for split in splits:
                upsert_vector(split, "chatacter_knowledge")
        if self.resp["UserSettings"] != "无":
            splits = self.resp["UserSettings"].split("<换行>")
            for split in splits:
                upsert_vector(split, "user")

        if self.resp["UserRealName"] != "无":
            self.context["relation"]["user_info"]["realname"] = self.resp["UserRealName"]
        if self.resp["UserHobbyName"] != "无":
            self.context["relation"]["user_info"]["hobbyname"] = self.resp["UserHobbyName"]
        if self.resp["UserDescription"] != "无":
            self.context["relation"]["user_info"]["description"] = self.resp["UserDescription"]

        if self.resp["CharacterPurpose"] != "无":
            self.context["relation"]["character_info"]["shortterm_purpose"] = self.resp["CharacterPurpose"]
        if self.resp["CharacterAttitude"] != "无":
            self.context["relation"]["character_info"]["attitude"] = self.resp["CharacterAttitude"]

        if self.resp["RelationDescription"] != "无":
            self.context["relation"]["relationship"]["description"] = self.resp["RelationDescription"]
        
        if int(self.resp["Dislike"]) is not None:
            if int(self.resp["Dislike"]) >= 0:
                self.context["relation"]["relationship"]["dislike"] = self.context["relation"]["relationship"]["dislike"] + int(self.resp["Dislike"]) - 5
            else:
                self.context["relation"]["relationship"]["dislike"] = self.context["relation"]["relationship"]["dislike"] + int(self.resp["Dislike"])
            
            if self.context["relation"]["relationship"]["dislike"] < 0:
                self.context["relation"]["relationship"]["dislike"] = 0
            if self.context["relation"]["relationship"]["dislike"] > 100:
                self.context["relation"]["relationship"]["dislike"] = 100

## Relations
# {
#     "_id": "xxx",
#     "uid": "xxx",
#     "cid": "xxx",
#     "user_info": {
#         "realname": "xxx",
#         "hobbyname": "xxx",
#         "description": "xxx",
#     },
#     "character_info": {
#         "longterm_purpose": "xxx",
#         "shortterm_purpose": "xxx",
#         "attitude": "xxx",
#     },
#     "relationship": {
#         "description": "xxx",
#         "closeness": xx,
#         "trustness": xx,
#     },
# }

# TASKPROMPT_总结_推理要求 = '''1. CharacterPublicSettings。总结最新聊天消息中，针对{character[platforms][wechat][nickname]}的新增的可公开人物设定。注意，如果这个信息跟{user[platforms][wechat][nickname]}有关，那么你不应该把它放到CharacterPublicSettings，而是CharacterPrivateSettings。
# 你可以总结出1条或者多条信息，每条消息为一行。
# 此处的格式可以参考”参考上下文“，使用"key：value"的形式，其中key可以由xxxx-xxx-xxx这样的多级格式构成；key是对信息的一个检索目录，而value是对它的详细描述（一般大于50字）。
# 如果你总结出的某一条信息，它的key（检索目录）与”参考上下文“中的某一条key应该是相同的，也就是你总结出的信息是对已知信息的一次更新，那么你应该将新总结的信息value与”参考上下文“中的已知信息value，进行融合合并，再写入你此处输出的value中。
# 如果没有什么有价值的信息，可以输出”无“。
# 2. CharacterPrivateSettings。总结最新聊天消息中，针对{character[platforms][wechat][nickname]}的新增的不可公开人物设定。这个设定信息通常是在描述{character[platforms][wechat][nickname]} 和 {user[platforms][wechat][nickname]}的关系或者聊天内容，不应该对其他人公开。在总结这个信息时，可以酌情标记具体时间。
# 格式或者内容要求同上。
# 3. UserSettings。总结最新聊天消息中，针对{user[platforms][wechat][nickname]}的新增的人物设定。
# 格式或者内容要求同上。
# 4. UserRealName。总结最新聊天消息中，{character[platforms][wechat][nickname]}知晓到的{user[platforms][wechat][nickname]}的真名。如果没有，你需要输出”无“。
# 5. UserHobbyName。总结最新聊天消息中，{character[platforms][wechat][nickname]}给{user[platforms][wechat][nickname]}起的亲密昵称。这可能是{user[platforms][wechat][nickname]}要求的，或者是{character[platforms][wechat][nickname]}主动起的。如果没有，你需要输出”无“。
# 6. UserDescription。总结最新聊天消息中，{character[platforms][wechat][nickname]}对{user[platforms][wechat][nickname]}印象描述。你需要结合”参考上下文“中的印象描述，进行更新。最多不超过100字。
# 7. CharacterPurpose。总结最新聊天消息中，{character[platforms][wechat][nickname]}的短期目标，可能跟多轮聊天有关，也可能无关。可以涉及一些隐式的长线心理活动，例如故意卖关子，故意激怒，假装欺骗等等。
# 8. CharacterAttitude。总结最新聊天消息中，{character[platforms][wechat][nickname]}对{user[platforms][wechat][nickname]}的态度。
# 9. RelationDescription。总结最新聊天消息中，{character[platforms][wechat][nickname]}和{user[platforms][wechat][nickname]}的关系变化。注意，他们之前的关系是"{relation[relationship][description]}",如果没有变化，你应该输出原关系。'''