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
import json

from framework.agent.base_agent import AgentStatus
from framework.agent.llmagent.doubao_llmagent import DouBaoLLMAgent
from conf.config import CONF
from volcenginesdkarkruntime import Ark

from qiaoyun.prompt.system_prompt import *
from qiaoyun.prompt.chat_taskprompt import *
from qiaoyun.prompt.chat_contextprompt import *
from qiaoyun.prompt.chat_noticeprompt import *
from qiaoyun.prompt.image_prompt import *

from util.time_util import timestamp2str

doubao_client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

# 需要 export ARK_API_KEY="xxxx"
class QiaoyunImageAnalyzeAgent(DouBaoLLMAgent):
    default_systemp_template = SYSTEMPROMPT_绘图

    default_userp_template = \
    "## 你的任务" + "\n" + \
    IMAGEPROMPT_绘图任务 + "\n" + \
    "\n" + \
    IMAGEPROMPT_绘图任务_推理 + "\n" + \
    IMAGEPROMPT_绘图任务_推理_要求 + "\n" + \
    "\n" + \
    "## 上下文" + "\n" + \
    CONTEXTPROMPT_人物信息 + "\n" + \
    "## {character[platforms][wechat][nickname]}的拍摄事件" + "\n" + \
    IMAGEPROMPT_绘图任务_推理_拍摄事件 + "\n" + \
    "\n" + \
    "## 注意事项" + "\n" + \
    IMAGEPROMPT_绘图任务_推理_注意事项

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

# 启动脚本
if __name__ == "__main__":
    from dao.user_dao import UserDAO
    from dao.mongo import MongoDBBase

    user_dao = UserDAO()
    target_user_alias = "qiaoyun"
    target_user_id = CONF["characters"][target_user_alias]
    character = user_dao.get_user_by_id(target_user_id)

    mongo = MongoDBBase()
    character_globals = mongo.find_many("embeddings", query={
        "metadata.type": "character_global",
        "metadata.cid": target_user_id
    })

    # for character_global in character_globals:
    #     print(character_global["key"])
    #     print(character_global["value"])
    
    print(len(character_globals))

    character_global = random.sample(character_globals, 1)[0]
    photo_event = character_global["key"] + "：" + character_global["value"]

    context = {
        "character": character,
        "photo_event": photo_event

    }

    c = QiaoyunImageAnalyzeAgent(context)
    results = c.run()
    for result in results:
        pass
    print()