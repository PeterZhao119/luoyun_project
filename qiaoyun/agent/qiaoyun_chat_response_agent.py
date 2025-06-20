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
import random

from framework.agent.base_agent import AgentStatus
from framework.agent.llmagent.doubao_llmagent import DouBaoLLMAgent
from conf.config import CONF
from volcenginesdkarkruntime import Ark

from qiaoyun.prompt.system_prompt import *
from qiaoyun.prompt.chat_taskprompt import *
from qiaoyun.prompt.chat_contextprompt import *
from qiaoyun.prompt.chat_noticeprompt import *

from util.time_util import str2timestamp

doubao_client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

# 需要 export ARK_API_KEY="xxxx"
class QiaoyunChatResponseAgent(DouBaoLLMAgent):
    default_systemp_template = SYSTEMPROMPT_小说越狱

    default_userp_template = \
    "## 你的任务" + "\n" + \
    TASKPROMPT_小说书写任务 + "\n" + \
    "\n" + \
    TASKPROMPT_微信对话 + "\n" + \
    TASKPROMPT_微信对话_推理要求_纯文本 + "\n" + \
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
    "## 注意事项" + "\n" + \
    NOTICE_常规注意事项_分段消息 + "\n" + \
    NOTICE_常规注意事项_生成优化 + "\n" + \
    NOTICE_常规注意事项_空输入处理

    default_output_schema = {
        "type": "object",
        "properties": {
            "InnerMonologue": {
                "type": "string",
                "description": "角色的内心独白"
            },
            "ChatResponse": {
                "type": "string",
                "description": "角色的回复，你可以在句子之间使用<换行>来表示分段，用来表示换行。"
            },
            # "RefinedChatResponse": {
            #     "type": "string",
            #     "description": "重新审视之后的改良回复。你可以在句子之间使用<换行>来表示分段，用来表示多段消息。"
            # },
            "MultiModalResponses": {
                "type": "array",
                "description": "角色的回复，可能包含多种类型。",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["text", "voice"],
                            "description": "消息的类型"
                        },
                        "content": {
                            "type": "string",
                            "description": "根据消息类型的不同，包含不同的内容"
                        },
                        "emotion": {
                            "type": "string",
                            "enum": ["无", "高兴","悲伤","愤怒","害怕","惊讶","厌恶","魅惑"],
                            "description": "仅对语音消息有效，表示语音的感情色彩"
                        },
                    },
                    "required": ["type", "content"],
                    "additionalProperties": True
                }
            },
            "ChatCatelogue": {
                "type": "string",
                "description": "在MultiModalResponses当中是否涉及角色所熟悉的知识，或者涉及她的专业知识，或者她的一些人设和故事。"
            },
            "RelationChange": {
                "type": "object",
                "description": "当下的关系变化",
                "properties": {
                    "Closeness": {
                        "type": "number",
                        "description": "亲密度数值变化",
                    },
                    "Trustness": {
                        "type": "number",
                        "description": "信任度数值变化",
                    },
                }
            },
            "FutureResponse": {
                "type": "object",
                "description": "假设用户在此之后一直没有任何回复，角色在未来什么时间可能进行再次的未来主动消息",
                "properties": {
                    "FutureResponseTime": {
                        "type": "string",
                        "description": "未来主动的消息时间，格式为xxxx年xx月xx日xx时xx分。",
                    },
                    "FutureResponseAction": {
                        "type": "string",
                        "description": "未来主动消息的大致内容，大约10-20个字。",
                    },
                }
            },
        }
    }

    def __init__(self, context=None, client=doubao_client, systemp_template=default_systemp_template, userp_template=default_userp_template, output_schema=default_output_schema, default_input=None, max_retries=3, name=None, stream=False, model="doubao_1.5_pro", extra_args=None):
        super().__init__(context, client, systemp_template, userp_template, output_schema, default_input, max_retries, name, stream, model, extra_args)

    def _posthandle(self):
        # 关系变化
        Closeness_Change = self.resp["RelationChange"]["Closeness"]
        Trustness_Change = self.resp["RelationChange"]["Trustness"]

        self.context["relation"]["relationship"]["closeness"] = self.context["relation"]["relationship"]["closeness"] + Closeness_Change
        if self.context["relation"]["relationship"]["closeness"] > 100:
            self.context["relation"]["relationship"]["closeness"] = 100
        if self.context["relation"]["relationship"]["closeness"] < 0:
            self.context["relation"]["relationship"]["closeness"] = 0
        
        self.context["relation"]["relationship"]["trustness"] = self.context["relation"]["relationship"]["trustness"] + Trustness_Change
        if self.context["relation"]["relationship"]["trustness"] > 100:
            self.context["relation"]["relationship"]["trustness"] = 100
        if self.context["relation"]["relationship"]["trustness"] < 0:
            self.context["relation"]["relationship"]["trustness"] = 0

        # Future Response
        if "proactive_times" not in self.context["conversation"]["conversation_info"]["future"]:
            self.context["conversation"]["conversation_info"]["future"]["proactive_times"] = 0
        future_proactive_times = self.context["conversation"]["conversation_info"]["future"]["proactive_times"]

        if self.resp["FutureResponse"]["FutureResponseAction"] != "无":
            if random.random() < (0.3 ** (future_proactive_times + 1) + 0.05):
                self.context["conversation"]["conversation_info"]["future"]["timestamp"] = str2timestamp(self.resp["FutureResponse"]["FutureResponseTime"])
                self.context["conversation"]["conversation_info"]["future"]["action"] = self.resp["FutureResponse"]["FutureResponseAction"]
                # self.context["conversation"]["conversation_info"]["proactive_times"] = self.context["conversation"]["conversation_info"]["proactive_times"] + 1
                logger.info("Book a new future action:" + str(self.context["conversation"]["conversation_info"]["future"]))
            else:
                self.context["conversation"]["conversation_info"]["future"]["timestamp"] = None
                self.context["conversation"]["conversation_info"]["future"]["action"] = None

