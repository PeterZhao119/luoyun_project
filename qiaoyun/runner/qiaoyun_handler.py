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

from qiaoyun.runner.qiaoyun_hardcode_handler import handle_hardcode, supported_hardcode
from qiaoyun.runner.context import context_prepare
from qiaoyun.util.message_util import send_message_via_context
from qiaoyun.agent.qiaoyun_chat_agent import QiaoyunChatAgent

from qiaoyun.tool.voice import qiaoyun_voice
from qiaoyun.tool.image import upload_image

max_handle_age = 3600 * 12 # 只处理12小时以内的消息

target_user_alias = "qiaoyun"
target_user_id = CONF["characters"][target_user_alias]

platform = "wechat"
typing_speed = 2.2
max_conversation_round = 50

conversation_dao = ConversationDAO()
user_dao = UserDAO()
lock_manager = MongoDBLockManager()
mongo = MongoDBBase()

async def main_handler():
    input_messages = []
    results = None
    lock = None
    try:
        # 获取顶部消息
        top_messages = read_top_inputmessages(to_user=target_user_id, status="pending", platform=platform, limit=16, max_handle_age=max_handle_age)
        if len(top_messages) == 0:
            # logger.info("no incoming message.")
            return
        
        for top_message in top_messages:
            logger.info("try handle message:")
            logger.info(top_message)

            # 获取user和character
            # 后面要优化新建的user的场景
            user = user_dao.get_user_by_id(top_message["from_user"])
            character = user_dao.get_user_by_id(top_message["to_user"])

            # 获取conversation并且上锁
            conversation_id, _ = conversation_dao.get_or_create_private_conversation(
                platform=platform,
                user_id1=user["platforms"][platform]["id"],
                nickname1=user["platforms"][platform]["nickname"],
                user_id2=character["platforms"][platform]["id"],
                nickname2=character["platforms"][platform]["nickname"],
            )
            conversation = conversation_dao.get_conversation_by_id(conversation_id)
            # 对conversation上锁
            lock = lock_manager.acquire_lock("conversation", conversation_id, timeout=120, max_wait=1)
            if lock is None:
                # 如果拿不到锁，证明当前message属于的conversation，正在被其他并发实例使用，则跳过这个message
                continue

        # 读取全部需要处理的消息，然后先置状态为handling
        input_messages = read_all_inputmessages(str(user["_id"]), str(character["_id"]), platform, "pending")
        for input_message in input_messages:
            input_message["status"] = "handling"
            save_inputmessage(input_message)
        
        conversation["conversation_info"]["input_messages"] = input_messages
        logger.info(input_messages)
        logger.info(conversation["conversation_info"])
        
        context = context_prepare(user, character, conversation)

        # 实际最终的返回过程        
        is_failed = False
        is_rollback = False
        is_clear = False
        is_hold = False
        is_hardfinish = False
        is_finish = False
        resp_messages = []

        # 处理拉黑逻辑
        if context["relation"]["relationship"]["dislike"] >= 100:
            outputmessage = send_message_via_context(
                context,
                message="[系统消息]已拉黑，如需恢复请联系作者LeanInWind",
                message_type="text",
                expect_output_timestamp = int(time.time())
            )
            is_finish = True

        # 处理硬指令
        elif str(context["user"]["_id"]) == CONF["admin_user_id"] and str(input_messages[0]["message"]).startswith(supported_hardcode):
            handle_hardcode(context, input_messages[0]["message"])
            outputmessage = send_message_via_context(
                context,
                message="ok",
                message_type="text",
                expect_output_timestamp = int(time.time())
            )
            is_hardfinish = True

        # 处理繁忙期状态
        elif context["relation"]["relationship"]["status"] not in ["空闲"]:
            logger.info("hold message as character busy...")
            is_hold = True

        else:
            c = QiaoyunChatAgent(context)
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

                # 判断因为新消息而卷回
                if is_new_message_coming_in(str(user["_id"]), str(character["_id"]), platform):
                    is_rollback = True
                    logger.info("roll back as new incoming message")
                    break

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

                    multimodal_responses_index = 0
                    for multimodal_response in multimodal_responses:
                        multimodal_responses_index = multimodal_responses_index + 1
                        # 处理声音
                        if multimodal_response["type"] == "voice":
                            voice_messages = qiaoyun_voice(multimodal_response["content"], multimodal_response["emotion"])
                            for voice_url, voice_length in voice_messages:
                                if multimodal_responses_index > 1:
                                    expect_output_timestamp = expect_output_timestamp + int(voice_length/1000) + random.randint(2,5)
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
                                
                                if multimodal_responses_index > 1:
                                    expect_output_timestamp = expect_output_timestamp + random.randint(2, 8)
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

                        # 处理其他情况（文本）
                        else:
                            text_message = str(multimodal_response["content"]).replace("<换行>", "\n")
                            if multimodal_responses_index > 1:
                                expect_output_timestamp = expect_output_timestamp + int(len(text_message)/typing_speed)
                            outputmessage = send_message_via_context(
                                context,
                                message=text_message,
                                message_type="text",
                                expect_output_timestamp = expect_output_timestamp
                            )

                            if outputmessage is not None:
                                resp_messages.append(outputmessage)

                        # 判断新消息，打断
                        if is_new_message_coming_in(str(user["_id"]), str(character["_id"]), platform):
                            is_rollback = True
                            logger.info("roll back as new incoming message")
                            break

                        if is_rollback:
                            break

        if is_failed:
            # 失败时，清理队列
            raise Exception("Handle fail: " + str(result))
        
        if is_hold:
            for input_message in input_messages:
                input_message["status"] = "hold"
                save_inputmessage(input_message)
            
            lock_manager.release_lock("conversation", conversation_id)
            return

        if is_hardfinish:
            for input_message in input_messages:
                input_message["status"] = "handled"
                save_inputmessage(input_message)
            
            lock_manager.release_lock("conversation", conversation_id)
            return
        
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

        for input_message in input_messages:
            input_message["status"] = "failed"
            save_inputmessage(input_message)
        
        lock_manager.release_lock("conversation", conversation_id)

        return 

    for input_message in input_messages:
        input_message["status"] = "handled"
        save_inputmessage(input_message)
    
    lock_manager.release_lock("conversation", conversation_id)

def is_new_message_coming_in(u_id, c_id, platform):
    input_messages = read_all_inputmessages(u_id, c_id, platform, "pending")
    return len(input_messages) > 0
    
