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

from bson import ObjectId
from entity.message import read_top_inputmessages, read_all_inputmessages, save_inputmessage
from dao.conversation_dao import ConversationDAO
from dao.user_dao import UserDAO
from dao.lock import MongoDBLockManager
from dao.mongo import MongoDBBase
from framework.agent.base_agent import AgentStatus
from conf.config import CONF

from qiaoyun.runner.context import context_prepare
from qiaoyun.util.message_util import send_message_via_context
from qiaoyun.agent.background.qiaoyun_future_message_agent import QiaoyunFutureMessageAgent
from qiaoyun.agent.daily.qiaoyun_daily_agent import QiaoyunDailyAgent

from qiaoyun.tool.voice import qiaoyun_voice
from qiaoyun.tool.image import upload_image
from util.time_util import date2str, timestamp2str


target_user_alias = "qiaoyun"
target_user_id = CONF["characters"][target_user_alias]

platform = "wechat"
typing_speed = 2.4
max_conversation_round = 50
descrease_frequency = 30240 # 多少秒降低一次关系数值
proactive_frequency = 5338 # 多少秒触发一次主动消息
proactive_chance = 0.03 # 多少概率触发

conversation_dao = ConversationDAO()
user_dao = UserDAO()
lock_manager = MongoDBLockManager()
mongo = MongoDBBase()

async def background_handler():
    is_decrease = False
    is_proactive = False
    # 一些固定处理
    now = int(time.time())
    mod = now % descrease_frequency
    if mod == 0:
        is_decrease = True
    
    mod = now % proactive_frequency
    if mod == 0:
        is_proactive = True

    if is_decrease:
        decrease_all()
    
    # 处理状态
    handle_status()

    # 生成每日脚本
    target_timestamp = int(time.time()) + 7200
    target_date = date2str(target_timestamp)
    find = mongo.find_one("dailynews", {"date": target_date, "cid": target_user_id})
    if find is None:
        logger.info("run daily agent...")
        character = user_dao.get_user_by_id(target_user_id)
        context = {
            "target_timestamp": target_timestamp,
            "character": character,
            "time_str": timestamp2str(target_timestamp, week=True),
            "date_str": date2str(target_timestamp, week=True)
        }

        c = QiaoyunDailyAgent(context)
        results = c.run()
        for result in results:
            if result["status"] != AgentStatus.FINISHED.value:
                continue
            logger.info(result["resp"])
    
    # 尝试主动消息
    if is_proactive:
        handle_proactive_message()
    
    # 处理待发送消息
    handle_pending_future_message()

def is_new_message_coming_in(u_id, c_id, platform):
    input_messages = read_all_inputmessages(u_id, c_id, platform, "pending")
    return len(input_messages) > 0

def decrease_all():
    logger.info("decrease all relationships...")
    relations = mongo.find_many("relations", query={"cid": target_user_id}, limit=10000)
    for relation in relations:
        if relation["relationship"]["closeness"] > 0 or relation["relationship"]["trustness"] > 0:
            relation["relationship"]["closeness"] = relation["relationship"]["closeness"] - 1
            relation["relationship"]["trustness"] = relation["relationship"]["trustness"] - 1
            if relation["relationship"]["closeness"] < 0:
                relation["relationship"]["closeness"] = 0
            if relation["relationship"]["trustness"] < 0:
                relation["relationship"]["trustness"] = 0
            mongo.replace_one("relations", {"_id": relation["_id"]}, relation)

def handle_status():
    now = int(time.time())
    date_str = date2str(int(time.time()))
    character = user_dao.get_user_by_id(target_user_id)
    current_script = mongo.find_one("dailyscripts", {"date": date_str, "cid": target_user_id, "start_timestamp": {"$lt": now}, "end_timestamp": {"$gt": now}})
    if current_script is not None:
        if current_script["action"] != character["user_info"]["status"]["action"]:
            logger.info("entering new script:" + str(current_script))
            # 更新当前活动脚本
            character["user_info"]["status"]["action"] = current_script["action"]
            character["user_info"]["status"]["place"] = current_script["place"]
            character["user_info"]["status"]["status"] = current_script["status"]
            mongo.replace_one("users", {"_id": ObjectId(target_user_id)}, character)
            # 按照概率更新对所有人的忙闲情况
            relations = mongo.find_many("relations", {"cid": target_user_id})
            for relation in relations:
                relation["relationship"]["status"] = current_script["status"]
                if current_script["status"] in ["繁忙"]:
                    chance = (relation["relationship"]["closeness"] + relation["relationship"]["trustness"]) / 150
                    if chance > random.random():
                        relation["relationship"]["status"] = "空闲"
                if current_script["status"] in ["睡觉"]:
                    chance = (relation["relationship"]["closeness"] + relation["relationship"]["trustness"]) / 480
                    if chance > random.random():
                        relation["relationship"]["status"] = "空闲"
                mongo.replace_one("relations", {"_id": relation["_id"]}, relation)

                # 如果为空闲，则调整所有该用户所有hold的message状态到pending
                mongo.update_many("inputmessages", {"from_user": relation["uid"], "to_user": relation["cid"], "status": "hold"}, {"$set": {"status": "pending"}})

def handle_proactive_message():
    # 先确保角色不在忙碌
    logger.info("start character proactive agent...")
    now = int(time.time())
    date_str = date2str(int(time.time()))
    character = user_dao.get_user_by_id(target_user_id)
    current_script = mongo.find_one("dailyscripts", {"date": date_str, "cid": target_user_id, "start_timestamp": {"$lt": now}, "end_timestamp": {"$gt": now}})
    if current_script is not None:
        if "status" not in character["user_info"]["status"]:
            character["user_info"]["status"]["status"] = "空闲"
        if character["user_info"]["status"]["status"] in ["空闲"]:
            # 拿到所有关系，确保关系适合发送
            logger.info("fetch all relations...")
            relations = mongo.find_many("relations", {"cid": target_user_id})
            for relation in relations:
                if relation["relationship"]["dislike"] >= 100:
                    continue
                if "status" not in relation["character_info"]:
                    relation["character_info"]["status"] = "空闲"
                if relation["character_info"]["status"] not in ["空闲"]:
                    continue
                user = user_dao.get_user_by_id(relation["uid"])
                character = user_dao.get_user_by_id(relation["cid"])
                conversation = conversation_dao.get_private_conversation(
                    "wechat",
                    user["platforms"]["wechat"]["id"],
                    character["platforms"]["wechat"]["id"],
                )
                if conversation is None:
                    continue
                if conversation["conversation_info"]["action"] is not None:
                    continue

                # 单次预期概率
                chance = ((relation["relationship"]["closeness"] + relation["relationship"]["trustness"]) / 200 + 0.5) * proactive_chance
                logger.info("chance: " + str(chance))
                if chance < random.random():
                    continue

                # 多次惩罚
                future_proactive_times = conversation["conversation_info"]["future"]["proactive_times"]
                if future_proactive_times > 0:
                    if random.random() > (0.3 ** future_proactive_times):
                        continue
                
                # 开始主动消息
                # 随机选择一个话题
                random_topics = [
                    "挑一条今天的新闻聊聊",
                    "聊一聊自己擅长的话题",
                    "聊一聊之前谈论过的话题"
                ]
                random_topic = random.sample(random_topics, 1)[0]
                logger.info("发起主动话题..." + random_topic)
                conversation["conversation_info"]["future"]["timestamp"] = int(time.time())
                conversation["conversation_info"]["future"]["action"] = random_topic

                mongo.replace_one("conversations", {"_id": conversation["_id"]}, conversation)

def handle_pending_future_message():
    # user_whitelist = "不辣的皮皮"
    results = None
    lock = None
    try:
        # 获取一条待处理消息
        # "future": { # 在该对话上规划的未来行动
        #     "timestamp": "xxx",
        #     "action": "xxx",
        #     "proactive_times": 0, # 主动对话次数，用来防止过度骚扰用户
        # }
        now = int(time.time())
        conversations = conversation_dao.find_conversations(query={
            "conversation_info.future.action": {
                "$ne": None,      # 值不等于null
                "$exists": True   # 字段必须存在
            },
            "conversation_info.future.timestamp": {
                "$lt": now,  # 到了发送时间
                "$gt": now - 1800 # 只发送半小时以内的
            },
            # "talkers.nickname": user_whitelist
        })
        if len(conversations) == 0:
            # logger.info("no incoming message.")
            return
        
        conversation = conversations[0]
        logger.info("try sending proactive message:" + str(conversation["conversation_info"]["future"]))

        users = user_dao.find_users({
            "platforms.wechat.id": conversation["talkers"][0]["id"]
        }, 1)
        user = users[0]
        characters = user_dao.find_users({
            "platforms.wechat.id": conversation["talkers"][1]["id"]
        }, 1)
        character = characters[0]

        conversation_id = str(conversation["_id"])
        lock = lock_manager.acquire_lock("conversation", conversation_id, timeout=120, max_wait=1)
        if lock is None:
            # 如果拿不到锁，证明当前message属于的conversation，正在被其他并发实例使用，则跳过这个message
            return
        
        context = context_prepare(user, character, conversation)

        # 实际最终的返回过程        
        is_failed = False
        is_rollback = False
        is_clear = False
        is_finish = False
        resp_messages = []

        # 处理拉黑逻辑
        if context["relation"]["relationship"]["dislike"] >= 100:
            # outputmessage = send_message_via_context(
            #     context,
            #     message="[系统消息]已拉黑，如需恢复请联系作者LeanInWind",
            #     message_type="text",
            #     expect_output_timestamp = int(time.time())
            # )
            is_finish = True
        else:

            c = QiaoyunFutureMessageAgent(context)
            results = c.run()

            # for result in results:
            #     pass
 
            for result in results:
                # result格式：status, message_queue, message, context
                # status: success, error, rollback, clear
                # message_queue: 发送的message_queue
                # context：最新的context情况，成功的话会更新context中的各段
                status = result["status"]
                logger.info("agent status: " + str(status))
                # logger.info("result: " + str(result))
                # logger.info("result: " + str(result))

                # 特殊状态的判断
                if status == AgentStatus.FAILED.value:
                    is_failed = True
                    break
                if status == AgentStatus.ROLLBACK.value:
                    is_rollback = True
                    break
                if status == AgentStatus.CLEAR.value:
                    is_clear = True
                    break
                if status == AgentStatus.FINISHED.value:
                    is_finish = True
                    break

                if status == AgentStatus.MESSAGE.value:
                    # 承接context
                    context = result["context"]

                    expect_output_timestamp = int(time.time())
                    multimodal_responses = result["resp"]["MultiModalResponses"]

                    for multimodal_response in multimodal_responses:
                        # 处理声音
                        if multimodal_response["type"] == "voice":
                            voice_messages = qiaoyun_voice(multimodal_response["content"], multimodal_response["emotion"])
                            for voice_url, voice_length in voice_messages:
                                outputmessage = send_message_via_context(
                                    context,
                                    message=multimodal_response["content"],
                                    message_type="voice",
                                    expect_output_timestamp = expect_output_timestamp,
                                    metadata={
                                        "url": voice_url,
                                        "voice_length": voice_length
                                    }
                                )

                                if outputmessage is not None:
                                    resp_messages.append(outputmessage)
                                
                                expect_output_timestamp = expect_output_timestamp + int(voice_length/1000) + random.randint(2,5)
                        # 处理照片
                        elif multimodal_response["type"] == "photo":
                            photo_id = str(multimodal_response["content"]).replace("「", "")
                            photo_id = photo_id.replace("」", "")
                            photo_id = photo_id.replace("照片", "", 1)
                            image_url = upload_image(photo_id)
                            if image_url is None:
                                pass
                            else:
                                # 增加频度惩罚
                                context["conversation"]["conversation_info"]["photo_history"].append(photo_id)
                                if len(context["conversation"]["conversation_info"]["photo_history"]) > 12:
                                    context["conversation"]["conversation_info"]["photo_history"] = context["conversation"]["conversation_info"]["photo_history"][-12:]

                                outputmessage = send_message_via_context(
                                    context,
                                    message=multimodal_response["content"],
                                    message_type="image",
                                    expect_output_timestamp = expect_output_timestamp,
                                    metadata={
                                        "url": image_url,
                                    }
                                )
                                logger.info("image message out:")
                                logger.info(outputmessage)

                                if outputmessage is not None:
                                    resp_messages.append(outputmessage)
                                
                                expect_output_timestamp = expect_output_timestamp + random.randint(2, 8)

                        # 处理其他情况（文本）
                        else:
                            text_message = str(multimodal_response["content"]).replace("<换行>", "\n")
                            outputmessage = send_message_via_context(
                                context,
                                message=text_message,
                                message_type="text",
                                expect_output_timestamp = expect_output_timestamp
                            )

                            if outputmessage is not None:
                                resp_messages.append(outputmessage)
                            
                            expect_output_timestamp = expect_output_timestamp + int(len(text_message)/typing_speed)

                        if is_rollback:
                            break

        if is_failed:
            # 失败时，清理队列
            raise Exception("Handle fail: " + str(result))
        
        if is_rollback or is_finish:
            conversation = context["conversation"]
            # 将pending_inputs放入history，再将返回放入history
            for input_message in conversation["conversation_info"]["input_messages"]:
                conversation["conversation_info"]["chat_history"].append(input_message)
            conversation["conversation_info"]["input_messages"] = []

            for resp_message in resp_messages:
                conversation["conversation_info"]["chat_history"].append(resp_message)
                # 同步更新到待总结区
            
            # 进行简单截断
            if len(conversation["conversation_info"]["chat_history"]) > max_conversation_round:
                conversation["conversation_info"]["chat_history"] = conversation["conversation_info"]["chat_history"][-max_conversation_round:]
        
            # 更新数据到conversation
            conversation_dao.update_conversation_info(
                conversation_id,
                conversation["conversation_info"]
            )

            # 更新relation
            mongo.replace_one("relations", 
                query={
                    "uid": context["relation"]["uid"],
                    "cid": context["relation"]["cid"],
                },
                update=context["relation"]
            )

    except Exception as e:
        logger.error(traceback.format_exc())

    conversation_dao.update_conversation_info(
        conversation_id,
        conversation["conversation_info"]
    )

    lock_manager.release_lock("conversation", conversation_id)
    
if __name__ == "__main__":
    now = int(time.time())

    date_str = date2str(int(time.time()))
    character = user_dao.get_user_by_id(target_user_id)
    # current_script = mongo.find_one("dailyscripts", {"date": date_str, "cid": target_user_id, "start_timestamp": {"$lt": now}, "end_timestamp": {"$gt": now}})

    current_scripts = mongo.find_many("dailyscripts", {"date": date_str, "cid": target_user_id, "start_timestamp": {"$gt": now}})

    print(current_scripts)
    print(now)

