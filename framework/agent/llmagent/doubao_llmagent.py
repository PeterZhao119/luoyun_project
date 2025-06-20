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
from framework.agent.llmagent.base_singleroundllmagent import BaseSingleRoundLLMAgent
from conf.config import CONF
from volcenginesdkarkruntime import Ark

doubao_client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

# 需要 export ARK_API_KEY="xxxx"
class DouBaoLLMAgent(BaseSingleRoundLLMAgent):
    def __init__(self, context = None, client=doubao_client, systemp_template = "", userp_template = "", output_schema = None, default_input = None, max_retries = 3, name = None, stream = False, model = "doubao_1.5_pro", extra_args = None):
        super().__init__(context, client, systemp_template, userp_template, output_schema, default_input, max_retries, name, stream, model, extra_args)
        if model in CONF["doubao_models"]:
            self.model = CONF["doubao_models"][model]

# 启动脚本
if __name__ == "__main__":
    context = {}
    c = DouBaoLLMAgent(context, userp_template='''{input}''', default_input={"input": "你好？"})
    responses = c.run()
    for response in responses:
        print(response)