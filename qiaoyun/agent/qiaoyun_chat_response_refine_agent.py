# -*- coding: utf-8 -*-
import os
import time

import sys
sys.path.append(".")
import json
import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

from framework.agent.base_agent import AgentStatus
from framework.agent.llmagent.doubao_llmagent import DouBaoLLMAgent
from conf.config import CONF
from volcenginesdkarkruntime import Ark

from qiaoyun.prompt.system_prompt import *
from qiaoyun.prompt.chat_taskprompt import *
from qiaoyun.prompt.chat_contextprompt import *
from qiaoyun.prompt.chat_noticeprompt import *

doubao_client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

# 需要 export ARK_API_KEY="xxxx"
class QiaoyunChatResponseRefineAgent(DouBaoLLMAgent):
    default_systemp_template = SYSTEMPROMPT_小说越狱_nojson

    default_userp_template = \
    "## 你的任务" + "\n" + \
    TASKPROMPT_小说书写任务_nojson + "\n" + \
    "\n" + \
    TASKPROMPT_微信对话_优化 + "\n" + \
    "\n" + \
    "## 上下文" + "\n" + \
    CONTEXTPROMPT_时间 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_新闻 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物信息 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物资料 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_用户资料 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物知识和技能 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物手机相册 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物状态 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_当前目标 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_当前的人物关系 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_历史对话 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_最新聊天消息 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_初步回复 + "\n" + \
    "\n" + \
    "## 注意事项" + "\n" + \
    NOTICE_优化注意事项_生成优化

    default_output_schema = None

    def __init__(self, context=None, client=doubao_client, systemp_template=default_systemp_template, userp_template=default_userp_template, output_schema=default_output_schema, default_input=None, max_retries=3, name=None, stream=False, model="deepseek_v3.1", extra_args=None):
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