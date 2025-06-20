import os
import time

import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

import sys
sys.path.append(".")

from dao.mongo import MongoDBBase

admin_user_name = "不辣的皮皮"
if __name__ == '__main__':
    mongo = MongoDBBase()

    characters = mongo.find_many("users", {"is_character": True})
    logger.info("characters:")
    for character in characters:
        logger.info(character["name"])
        logger.info(str(character["_id"]))
        logger.info(character)
    
    users = mongo.find_many("users", {"platforms.wechat.nickname": admin_user_name})
    logger.info("admin user:")
    for user in users:
        logger.info(user["name"])
        logger.info(str(user["_id"]))
        logger.info(user)



