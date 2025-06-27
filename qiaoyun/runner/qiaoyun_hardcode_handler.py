import sys
sys.path.append(".")
import copy
import os
import time
import random
import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

from entity.message import read_top_inputmessages, read_all_inputmessages, save_inputmessage
from dao.conversation_dao import ConversationDAO
from dao.user_dao import UserDAO
from dao.lock import MongoDBLockManager
from dao.mongo import MongoDBBase
from framework.agent.base_agent import AgentStatus
from conf.config import CONF
from qiaoyun.tool.image import upload_image
from util.time_util import date2str

from connector.ecloud.ecloud_api import Ecloud_API
from bson import ObjectId

target_user_alias = "qiaoyun"
supported_hardcode = ("朋友圈 ", "删除 ", "重新生成")

def handle_hardcode(context, message):
    mongo = MongoDBBase()
    if str(message).startswith("删除 "):
        pid = str(message).replace("删除 ", "")
        pid = pid.strip()
        mongo.delete_vector("embeddings", pid)

    if str(message).startswith("朋友圈 "):
        pid = str(message).replace("朋友圈 ", "")
        pid = pid.strip()
        photo = mongo.get_vector_by_id("embeddings", pid)
        pyq_post = photo["metadata"]["pyqpost"]

        image_url = upload_image(pid)

        data = {
            "wId": CONF["ecloud"]["wId"][target_user_alias],
            "content": pyq_post,
            "paths": image_url
        }

        resp_json = Ecloud_API.snsSendImage(data)
        logger.info(resp_json)
    
    if str(message).startswith("重新生成"):
        target_user_id = CONF["characters"][target_user_alias]

        date_str = date2str(int(time.time()) + 7200)
        mongo.delete_one("dailynews", {"cid": target_user_id, "date": date_str})
