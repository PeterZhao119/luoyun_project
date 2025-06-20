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

from qiaoyun.prompt.system_prompt import *
from qiaoyun.prompt.chat_taskprompt import *
from qiaoyun.prompt.chat_contextprompt import *
from qiaoyun.prompt.chat_noticeprompt import *

doubao_client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

# 需要 export ARK_API_KEY="xxxx"
class QiaoyunFutureQueryRewriteAgent(DouBaoLLMAgent):
    default_systemp_template = SYSTEMPROMPT_小说越狱

    default_userp_template = \
    "## 你的任务" + "\n" + \
    TASKPROMPT_小说书写任务 + "\n" + \
    "\n" + \
    TASKPROMPT_未来_语义理解 + "\n" + \
    TASKPROMPT_语义理解_推理要求 + "\n" + \
    "\n" + \
    "## 上下文" + "\n" + \
    CONTEXTPROMPT_时间 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_新闻 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物信息 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_人物状态 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_当前目标 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_当前的人物关系 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_历史对话 + "\n" + \
    "\n" + \
    CONTEXTPROMPT_规划行动

    default_output_schema = {
        "type": "object",
        "properties": {
            "InnerMonologue": {
                "type": "string",
                "description": "角色的内心独白"
            },
            "CharacterSettingQueryQuestion": {
                "type": "string",
                "description": "你认为针对角色人物设定需要进行的查询语句，不要为空。"
            },
            "CharacterSettingQueryKeywords": {
                "type": "string",
                "description": "你认为针对角色人物设定需要进行的查询关键词，不要为空。"
            },
            "UserProfileQueryQuestion": {
                "type": "string",
                "description": "你认为针对用户资料需要进行的查询语句，不要为空。"
            },
            "UserProfileQueryKeywords": {
                "type": "string",
                "description": "你认为针对用户资料需要进行的查询关键词，不要为空。"
            },
            "CharacterKnowledgeQueryQuestion": {
                "type": "string",
                "description": "你认为针对角色的知识与技能需要进行的查询语句，不要为空。"
            },
            "CharacterKnowledgeQueryKeywords": {
                "type": "string",
                "description": "你认为针对角色的知识与技能需要进行的查询关键词，不要为空。"
            },
            "CharacterPhotoQueryQuestion": {
                "type": "string",
                "description": "你认为针对角色的手机相册需要进行的查询语句，不要为空。"
            },
            "CharacterPhotoQueryKeywords": {
                "type": "string",
                "description": "你认为针对角色的手机相册需要进行的查询关键词，不要为空。"
            }
        }
    }

    def __init__(self, context=None, client=doubao_client, systemp_template=default_systemp_template, userp_template=default_userp_template, output_schema=default_output_schema, default_input=None, max_retries=3, name=None, stream=False, model="doubao_1.5_pro", extra_args=None):
        super().__init__(context, client, systemp_template, userp_template, output_schema, default_input, max_retries, name, stream, model, extra_args)

# 启动脚本
if __name__ == "__main__":
    context = {}
    c = QiaoyunFutureQueryRewriteAgent(context)
    print(c.userp_template)