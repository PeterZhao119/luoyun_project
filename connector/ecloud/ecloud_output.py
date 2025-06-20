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
import asyncio

from dao.mongo import MongoDBBase
from dao.user_dao import UserDAO
from entity.message import save_outputmessage
from conf.config import CONF
from connector.ecloud.ecloud_api import Ecloud_API
from connector.ecloud.ecloud_adapter import std_to_ecloud_message

async def run_ecloud_output():
    while True:
        await asyncio.sleep(1)
        await output_handler()

async def main():
    await asyncio.gather(
        run_ecloud_output()
    )

async def output_handler():
    mongo = MongoDBBase()
    user_dao = UserDAO()

    try:
        # 寻找要发送的message
        now = int(time.time())
        message = mongo.find_one("outputmessages", {
            "platform": "wechat",
            # "from_user": target_user_id,
            "status": "pending",
            "expect_output_timestamp": {"$lt": now},  # 预期输出的时间戳秒级
        })

        if message is None:
            return
        
        logger.info("sending...")
        logger.info(message)

        target_user_id = message["from_user"]

        character = user_dao.get_user_by_id(target_user_id)
        if character is None:
            raise Exception("character not found: " + str(target_user_id))

        # 确定输出人wcid
        user = user_dao.get_user_by_id(message["to_user"])
        if user is None:
            raise Exception("character not found: " + str(target_user_id))
        
        target_user_alias = character["name"]
        wid = CONF["ecloud"]["wId"][target_user_alias]
        target_user_id = CONF["characters"][target_user_alias]
        
        # 实际发送
        ecloud = std_to_ecloud_message(message)
        ecloud["wId"] = wid
        if message["chatroom_name"] is None:
            ecloud["wcId"] = user["platforms"]["wechat"]["account"]
        else:
            ecloud["wcId"] = message["chatroom_name"]

        logger.info("sending ecloud message...")
        logger.info(ecloud)

        # 分类型发送消息
        resp_json = {"code": 1001}
        if message["message_type"] in ["text"]:
            resp_json = Ecloud_API.sendText(ecloud)
        if message["message_type"] in ["voice"]:
            resp_json = Ecloud_API.sendVoice(ecloud)
            if resp_json["code"] != "1000":
                logger.info("sending voice error, fall back to text")
                message["message_type"] = "text"
                ecloud = std_to_ecloud_message(message)
                ecloud["wId"] = wid
                if message["chatroom_name"] is None:
                    ecloud["wcId"] = user["platforms"]["wechat"]["account"]
                else:
                    ecloud["wcId"] = message["chatroom_name"]
                resp_json = Ecloud_API.sendText(ecloud)
        if message["message_type"] in ["image"]:
            resp_json = Ecloud_API.sendImage(ecloud)

        logger.info(resp_json)
        
        now = int(time.time())
        message["status"] = "handled"
        message["handled_timestamp"] = now
        save_outputmessage(message)

    except Exception as e:
        logger.error(traceback.format_exc())
        now = int(time.time())
        message["status"] = "failed"
        message["handled_timestamp"] = now
        save_outputmessage(message)


if __name__ == '__main__':
    asyncio.run(main())