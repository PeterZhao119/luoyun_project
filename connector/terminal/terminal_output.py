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
import json
from bson import ObjectId

from dao.mongo import MongoDBBase
from dao.user_dao import UserDAO
from entity.message import save_outputmessage

# big
from_user = "680ba9871ce4b5edce83a0e5"
to_user = "680ba9821ce4b5edce83a0de"

# small
from_user = "680b519151a0ae0f436c3c5a"
to_user = "680b529751a0ae0f436c3c74"


mongo = MongoDBBase()
user_dao = UserDAO()
user = user_dao.get_user_by_id(from_user)
user_name = user["platforms"]["wechat"]["nickname"]

while True:
    time.sleep(1)
    now = int(time.time())
    message = mongo.find_one("outputmessages", {
        "platform": "wechat",
        "from_user": from_user,
        "to_user": to_user,
        "status": "pending",
        "expect_output_timestamp": {"$lt": now},  # 预期输出的时间戳秒级
    })

    if message is None:
        continue

    now = int(time.time())
    print(user_name + "：" + message["message"])
    print()

    message["status"] = "handled"
    message["handled_timestamp"] = now

    save_outputmessage(message)
