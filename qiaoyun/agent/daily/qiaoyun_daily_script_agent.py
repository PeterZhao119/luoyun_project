# -*- coding: utf-8 -*-
import os
import time
import json
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
from util.time_util import date2str, str2timestamp

from qiaoyun.prompt.system_prompt import *
from qiaoyun.prompt.chat_taskprompt import *
from qiaoyun.prompt.chat_contextprompt import *
from qiaoyun.prompt.chat_noticeprompt import *
from qiaoyun.prompt.chat_dailyprompt import *

doubao_client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

# 需要 export ARK_API_KEY="xxxx"
class QiaoyunDailyScriptAgent(DouBaoLLMAgent):
    default_systemp_template = SYSTEMPROMPT_小说越狱

    default_userp_template = \
    "## 你的任务" + "\n" + \
    TASKPROMPT_小说书写任务 + "\n" + \
    "\n" + \
    DAILYPROMPT_活动剧本生成 + "\n" + \
    "\n" + \
    DAILYPROMPT_活动剧本生成_推理要求 + "\n" + \
    "\n" + \
    "## 参考上下文" + "\n" + \
    DAILYPROMPT_日期 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物信息 + "\n" + \
    "\n" + \
    DAILYPROMPT_个人偏好 + "\n" + \
    "\n" + \
    DAILYPROMPT_新闻资讯 + "\n" + \
    "\n" + \
    DAILYPROMPT_活动剧本生成_注意事项 + "\n"

    def __init__(self, context=None, client=doubao_client, systemp_template=default_systemp_template, userp_template=default_userp_template, output_schema=None, default_input=None, max_retries=3, name=None, stream=False, model="doubao_1.6_pro", extra_args=None):
        super().__init__(context, client, systemp_template, userp_template, output_schema, default_input, max_retries, name, stream, model, extra_args)

    def _posthandle(self):
        resp_raw = str(self.resp)
        resp_raw = resp_raw.removeprefix("json")
        resp_raw = resp_raw.removeprefix("```")
        resp_raw = resp_raw.removesuffix("```")

        start_idx = resp_raw.find('[')
        end_idx = resp_raw.rfind(']')
        
        # 有效性校验（需同时满足三个条件）
        if start_idx == -1 or end_idx == -1 or start_idx > end_idx:
            pass
        else:
            resp_raw = resp_raw[start_idx : end_idx+1]
            
        try:
            resp_json = json.loads(resp_raw)
        except:
            resp_json = resp_raw
        
        self.resp = resp_json

        # 写入数据库
        date_str = date2str(self.context["target_timestamp"])
        mongo = MongoDBBase()
        mongo.delete_many("dailyscripts", {"date": date_str, "cid": str(self.context["character"]["_id"])})

        for script in self.resp:
            start_timestamp = str2timestamp(date_str+script["Starttime"])
            end_timestamp = str2timestamp(date_str+script["Endtime"])
            script_json = {
                "cid": str(self.context["character"]["_id"]),
                "date": date_str,
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "action": script["Action"],
                "action_short": script["Action_Short"],
                "place": script["Place"],
                "status": script["Status"],
            }
            mongo.insert_one("dailyscripts", script_json)