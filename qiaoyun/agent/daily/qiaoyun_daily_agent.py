# -*- coding: utf-8 -*-
import os
import time
import copy

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
from framework.tool.search.aliyun import aliyun_search
from qiaoyun.agent.daily.qiaoyun_daily_learning_agent import QiaoyunDailyLearningAgent
from qiaoyun.agent.daily.qiaoyun_daily_script_agent import QiaoyunDailyScriptAgent
from qiaoyun.agent.daily.qiaoyun_image_analyze_agent import QiaoyunImageAnalyzeAgent

from dao.mongo import MongoDBBase
from dao.user_dao import UserDAO
from util.embedding_util import upsert_one

from qiaoyun.tool.image import generate_qiaoyun_image, generate_qiaoyun_image_save
from util.time_util import timestamp2str, date2str
from qiaoyun.util.message_util import send_message
from qiaoyun.tool.image import upload_image

random_topic_number = 3
image_script_number = 4
image_count = 1
jsonl_file = "qiaoyun/role/qiaoyun/role_image.jsonl"
mongo = MongoDBBase()
user_dao = UserDAO()

class QiaoyunDailyAgent(BaseAgent):
    def __init__(self, context = None, max_retries = 3, name = None):
        super().__init__(context, max_retries, name)
    
    def _execute(self):
        self.context["daily"] = {
            "random_embeddings": [], # 随机人设
            "search_results": [], # 搜索结果
        }
        # 生成搜索话题
        # 固定话题 加 随机人设进行召回生成话题

        logger.info("searching for daily topics")
        now_str = timestamp2str(self.context["target_timestamp"], week=True)
        search_topics = [
            "今天是" + now_str + "。我的特长是：心理剖析（瞬间读懂对方真实动机和心理弱点），危机公关（在舆论风暴中优雅地化解品牌危机），精准打击（用最温柔的语气说最扎心的话），社交操控（在各种场合如鱼得水，暗中布局人脉，信息挖掘（善于从细节中获取有价值的情报）。请帮忙搜索今天与我特长相关的最新相关新闻、资讯、热点话题；偏好城市上海周边；选择较为有趣或者引人注目的内容，排除天气相关话题。输出1-3条内容，每条大约200字的内容，仅包括消息正文，不要包括总结或分析。",
            "今天是" + now_str + "。我的爱好是：研读犯罪心理学案例，品鉴小众精酿啤酒，收集各国古董首饰，深夜听悬疑播客，偶尔玩剧本杀当凶手。请帮忙搜索今天与我爱好相关的最新相关新闻、资讯、热点话题；偏好城市上海周边；。选择较为有趣或者引人注目的内容，输出2-4条内容，每条大约200字的内容，仅包括消息正文，不要包括总结或分析。",
            "今天是" + now_str + "。我居住的城市是上海市。请帮忙搜索当地今天最新的相关新闻、资讯、热点话题；尤其是娱乐、科技、天气方向的。选择较为有趣或者引人注目的内容，输出2-4条内容，每条大约200字的内容，仅包括消息正文，不要包括总结或分析。",
        ]

        random_embeddings_number = mongo.count_documents("embeddings", query={"metadata.type": "character_global"})
        all_embeddings = mongo.find_many("embeddings", query={"metadata.type": "character_global"}, limit=random_embeddings_number)
        if len(all_embeddings) > random_topic_number:
            random_embeddings = random.sample(all_embeddings, random_topic_number)
        else:
            random_embeddings = all_embeddings
        
        for random_embedding in random_embeddings:
            search_topics.append("今天是" + now_str + "。我有一个关注的方向是，" + random_embedding["key"] + "："  + random_embedding["value"] + "\n请帮忙搜索与其相关的最新新闻、资讯、热点话题；尤其是娱乐、旅游、科技方向的。输出2-4条内容，每条大约200字的内容，仅包括消息正文，不要包括总结或分析。")
            self.context["daily"]["random_embeddings"].append(random_embedding["key"] + "："  + random_embedding["value"])

        # 搜索
        for search_topic in search_topics:
            logger.info("search for: " + search_topic)
            search_result = aliyun_search(
                messages=[{
                    "role": "user",
                    "content": search_topic
                }
                ])
            self.context["daily"]["search_results"].append(search_result)
            logger.info(search_result)
        
        # 上下文整理
        self.context["daily"]["random_embeddings_str"] = "\n".join(self.context["daily"]["random_embeddings"])
        self.context["daily"]["search_results_str"] = "\n".join(self.context["daily"]["search_results"])

        # 学习进当日新闻和知识库
        c = QiaoyunDailyLearningAgent(self.context)
        results = c.run()
        for result in results:
            if result["status"] != AgentStatus.FINISHED.value:
                continue
            self.context["daily"]["news"] = result["resp"]["News"]

        # 生成每日活动脚本
        c = QiaoyunDailyScriptAgent(self.context)
        results = c.run()
        for result in results:
            if result["status"] != AgentStatus.FINISHED.value:
                continue
            self.context["daily"]["scripts"] = result["resp"]

        # 生成图片和朋友圈文案
        if len(self.context["daily"]["scripts"]) > image_script_number:
            random_scripts = random.sample(self.context["daily"]["scripts"], image_script_number)
        else:
            random_scripts = copy.deepcopy(self.context["daily"]["scripts"])
        
        for random_script in random_scripts:
            try:
                self.context["photo_event"] = random_script["Starttime"] + "。" + random_script["Place"] + "。" + random_script["Action"]
                c = QiaoyunImageAnalyzeAgent(self.context)
                results = c.run()
                for result in results:
                    if result["status"] != AgentStatus.FINISHED.value:
                        continue
                    image_infos = result["resp"]
                
                image_info = random.sample(image_infos,1)[0]
                prompt = image_info["EnglishDescription"]
                mode = 0
                if image_info["PhotoType"] in ["静物照"]:
                    mode = 1
                sub_mode = image_info["PhotoSubType"]
                if image_info["Orientation"] in ["纵向"]:
                    resizedWidth = 768
                    resizedHeight = 1024
                else:
                    resizedWidth = 1024
                    resizedHeight = 768
            
                task_id = generate_qiaoyun_image(prompt, image_count, mode, sub_mode, resizedWidth, resizedHeight)
                origin_paths, saved_paths = generate_qiaoyun_image_save(task_id)

                for i in range(len(saved_paths)):
                    image_info["origin_path"] = origin_paths[i]
                    image_info["saved_path"] = saved_paths[i]
                    image_info["character_global_key"] = random_script["Action_Short"]
                    image_info["character_global_value"] = random_script["Action"]

                    logger.info(image_info)

                    with open(jsonl_file, "a") as f:
                        f.write(json.dumps(image_info, ensure_ascii=False) + "\n")
                    
                    # 写入向量库
                    key = image_info["character_global_key"]
                    value = "【照片故事】" + image_info["Extension"] + "【照片描述】" + image_info["Description"]

                    eid = upsert_one(key, value, metadata={
                        "type": "character_photo",
                        "uid": None,
                        "cid": str(self.context["character"]["_id"]),
                        "url": image_info["origin_path"],
                        "file": image_info["saved_path"],
                        "pyqpost": image_info["PYQPost"],
                    })
                    image_url = upload_image(eid)

                    # 发送给管理员
                    outputmessage = send_message(
                        platform="wechat",
                        from_user=str(self.context["character"]["_id"]),
                        to_user=CONF["admin_user_id"],
                        chatroom_name=None,
                        message=str(eid),
                        message_type = "image",
                        metadata = {
                            "url" : image_url
                        }
                    )
                    outputmessage = send_message(
                        platform="wechat",
                        from_user=str(self.context["character"]["_id"]),
                        to_user=CONF["admin_user_id"],
                        chatroom_name=None,
                        message=random_script["Starttime"],
                        message_type = "text",
                    )
                    outputmessage = send_message(
                        platform="wechat",
                        from_user=str(self.context["character"]["_id"]),
                        to_user=CONF["admin_user_id"],
                        chatroom_name=None,
                        message=str(eid),
                        message_type = "text",
                    )
                    outputmessage = send_message(
                        platform="wechat",
                        from_user=str(self.context["character"]["_id"]),
                        to_user=CONF["admin_user_id"],
                        chatroom_name=None,
                        message=image_info["PYQPost"],
                        message_type = "text",
                    )

            except Exception as e:
                logger.error(traceback.format_exc())

        yield self.context["daily"]

if __name__ == "__main__":
    target_user_alias = "qiaoyun"
    target_user_id = CONF["characters"][target_user_alias]
    character = user_dao.get_user_by_id(target_user_id)

    date_str = date2str(int(time.time()) + 7200)
    mongo.delete_one("dailynews", {"cid": target_user_id, "date": date_str})

    # target_user_alias = "qiaoyun"
    # target_user_id = CONF["characters"][target_user_alias]
    # character = user_dao.get_user_by_id(target_user_id)
    # context = {
    #     "character": character,
    #     "time_str": timestamp2str(int(time.time()), week=True),
    #     "date_str": date2str(int(time.time()), week=True)
    # }

    # c = QiaoyunDailyAgent(context)
    # results = c.run()
    # for result in results:
    #     if result["status"] != AgentStatus.FINISHED.value:
    #         continue
    #     print(result["resp"])
