import sys
sys.path.append(".")
import copy
import os
import time
import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)
import random
import json

from bson import ObjectId
from dao.user_dao import UserDAO
from util.embedding_util import upsert_one

from conf.config import CONF

from framework.agent.base_agent import AgentStatus, BaseAgent
from qiaoyun.agent.daily.qiaoyun_image_analyze_agent import QiaoyunImageAnalyzeAgent
from qiaoyun.tool.image import generate_qiaoyun_image, generate_qiaoyun_image_save

start_index = 0
image_count = 2
jsonl_file = "qiaoyun/role/qiaoyun/role_image.jsonl"
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

    character_globals = character_globals[start_index:]
    
    for character_global in character_globals:
        try:
            photo_event = character_global["key"] + "：" + character_global["value"]

            context = {
                "character": character,
                "photo_event": photo_event
            }

            c = QiaoyunImageAnalyzeAgent(context)
            results = c.run()
            image_infos = []
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
            try:
                task_id = generate_qiaoyun_image(prompt, image_count, mode, sub_mode, resizedWidth, resizedHeight)
                origin_paths, saved_paths = generate_qiaoyun_image_save(task_id)

                for i in range(len(saved_paths)):
                    image_info["origin_path"] = origin_paths[i]
                    image_info["saved_path"] = saved_paths[i]
                    image_info["character_global_key"] = character_global["key"]
                    image_info["character_global_value"] = character_global["value"]

                    with open(jsonl_file, "a") as f:
                        f.write(json.dumps(image_info, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error(traceback.format_exc())

        except Exception as e:
            logger.error(traceback.format_exc())
                

    