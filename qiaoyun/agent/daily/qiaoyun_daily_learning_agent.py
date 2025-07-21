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
from util.time_util import date2str

from qiaoyun.prompt.system_prompt import *
from qiaoyun.prompt.chat_taskprompt import *
from qiaoyun.prompt.chat_contextprompt import *
from qiaoyun.prompt.chat_noticeprompt import *
from qiaoyun.prompt.chat_dailyprompt import *

doubao_client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

# 需要 export ARK_API_KEY="xxxx"
class QiaoyunDailyLearningAgent(DouBaoLLMAgent):
    default_systemp_template = SYSTEMPROMPT_资讯分析

    default_userp_template = \
    "## 你的任务" + "\n" + \
    DAILYPROMPT_资讯分析 + "\n" + \
    "\n" + \
    DAILYPROMPT_资讯分析_推理要求 + "\n" + \
    "\n" + \
    "## 参考上下文" + "\n" + \
    DAILYPROMPT_时间 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物信息 + "\n" + \
    "\n" + \
    DAILYPROMPT_个人偏好 + "\n" + \
    "\n" + \
    DAILYPROMPT_新闻资讯 + "\n"

    default_output_schema = {
        "type": "object",
        "properties": {
            "KnowledgePoints": {
                "type": "array",
                "description": "知识点数组，输出为json的字符串数组形式。请提取3-5个最有学习价值，或者最有意思的知识点，控制好数量。",
                "items": {
                    "type": "string",
                    "description": "其中每个知识点的格式，请参考“个人偏好”中的格式，以“key：value”形式的字符串来表达。其中：value是该信息的原文。key是对value的一个总结，key的格式是目录式的xxx-xxx-xxxx，目录分层可以参考“个人偏好”的内容。"
                }
            },
            "News": {
                "type": "string",
                "description": "请提取3-5个最有意思，或者最有价值的新闻，合并为一段新闻文稿。可以适当换行，但是不要有空行；不需要精简，保持新闻原文。"
            }
        }
    }

    def __init__(self, context=None, client=doubao_client, systemp_template=default_systemp_template, userp_template=default_userp_template, output_schema=default_output_schema, default_input=None, max_retries=3, name=None, stream=False, model="doubao_1.5_pro", extra_args=None):
        super().__init__(context, client, systemp_template, userp_template, output_schema, default_input, max_retries, name, stream, model, extra_args)

    def _posthandle(self):
        # 存储新闻
        news = self.resp["News"]
        target_date = date2str(self.context["target_timestamp"])

        daily_news = {
            "cid": str(self.context["character"]["_id"]),
            "news": news,
            "date": target_date
        }

        mongo = MongoDBBase()
        
        find = mongo.find_one("dailynews", {"date": target_date, "cid": str(self.context["character"]["_id"])})
        if find is None:
            mongo.insert_one("dailynews", daily_news)
        else:
            mongo.replace_one("dailynews",  {"date": target_date, "cid": str(self.context["character"]["_id"])}, daily_news)
        
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
        
        for knowledge in self.resp["KnowledgePoints"]:
            upsert_vector(knowledge, "character_knowledge")