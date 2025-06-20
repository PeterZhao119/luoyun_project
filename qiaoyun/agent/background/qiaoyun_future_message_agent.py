# -*- coding: utf-8 -*-
import os
import time

import sys
sys.path.append(".")
import random
import json
import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

from framework.agent.base_agent import AgentStatus, BaseAgent
from conf.config import CONF
from volcenginesdkarkruntime import Ark

# from qiaoyun.agent.qiaoyun_query_rewrite_agent import QiaoyunQueryRewriteAgent
from qiaoyun.agent.background.qiaoyun_future_query_rewrite_agent import QiaoyunFutureQueryRewriteAgent
# from qiaoyun.agent.qiaoyun_chat_response_agent import QiaoyunChatResponseAgent
from qiaoyun.agent.background.qiaoyun_future_chat_response_agent import QiaoyunFutureChatResponseAgent
from qiaoyun.agent.qiaoyun_context_retrieve_agent import QiaoyunContextRetrieveAgent
# from qiaoyun.agent.qiaoyun_chat_response_refine_agent import QiaoyunChatResponseRefineAgent
from qiaoyun.agent.background.qiaoyun_future_chat_response_refine_agent import QiaoyunFutureChatResponseRefineAgent
from qiaoyun.agent.qiaoyun_post_analyze_agent import QiaoyunPostAnalyzeAgent


# 触发r1做优化的概率
default_refine_chance = 0.15
refine_chance = 0.6

class QiaoyunFutureMessageAgent(BaseAgent):
    def __init__(self, context = None, max_retries = 3, name = None):
        super().__init__(context, max_retries, name)
    
    def _execute(self):
        # 问题重写
        c = QiaoyunFutureQueryRewriteAgent(self.context)
        results = c.run()
        for result in results:
            if result["status"] != AgentStatus.FINISHED.value:
                continue
            self.context["query_rewrite"] = result["resp"]
        
        # 上下文拉取
        c = QiaoyunContextRetrieveAgent(self.context)
        results = c.run()
        for result in results:
            if result["status"] != AgentStatus.FINISHED.value:
                continue
            self.context["context_retrieve"] = result["resp"]

        # 回复生成
        c = QiaoyunFutureChatResponseAgent(self.context)
        results = c.run()
        for result in results:
            if result["status"] != AgentStatus.FINISHED.value:
                continue
            logger.info(result["resp"])
            self.resp = result["resp"]
            self.context["MultiModalResponses"] = result["resp"]["MultiModalResponses"]
        
        # 如果涉及到可扩展内容，有概率调用细化链路
        is_refine = False
        if random.random() < default_refine_chance:
            is_refine = True
        if 'ChatCatelogue' in self.resp:
            if self.resp["ChatCatelogue"] == "是" and random.random() < refine_chance:
                is_refine = True
        
        if is_refine:
            logger.info("refining with r1...")
            c = QiaoyunFutureChatResponseRefineAgent(self.context)
            results = c.run()
            for result in results:
                if result["status"] != AgentStatus.FINISHED.value:
                    continue
                logger.info(result["resp"])
                self.resp["MultiModalResponses"] = result["resp"]
                self.context["MultiModalResponses"] = result["resp"]
        
        self.status = AgentStatus.MESSAGE
        yield self.resp
        self.status = AgentStatus.RUNNING

        c = QiaoyunPostAnalyzeAgent(self.context)
        results = c.run()
        for result in results:
            if result["status"] != AgentStatus.FINISHED.value:
                continue
            logger.info(result["resp"])

        

        