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

from bson import ObjectId

from dao.mongo import MongoDBBase
from util.time_util import timestamp2str, date2str
from qiaoyun.util.message_util import messages_to_str

def context_prepare(user, character, conversation):
    context = {
        "user": user,
        "character": character,
        "conversation": conversation
    }

    mongo = MongoDBBase()
    relation = mongo.find_one("relations", {"uid": str(user["_id"]), "cid": str(character["_id"])})
    if relation is None:
        realtion_id = mongo.insert_one("relations", get_default_relation(user, character, conversation["platform"]))
        relation = mongo.find_one("relations", {"_id": ObjectId(realtion_id)})

    if "chat_history" not in context["conversation"]["conversation_info"]:
        context["conversation"]["conversation_info"]["chat_history"] = []
    if "input_messages" not in context["conversation"]["conversation_info"]:
        context["conversation"]["conversation_info"]["input_messages"] = []
    
    if "photo_history" not in context["conversation"]["conversation_info"]:
        context["conversation"]["conversation_info"]["photo_history"] = []

    if "future" not in context["conversation"]["conversation_info"]:
        context["conversation"]["conversation_info"]["future"] = {
            "timestamp": None,
            "action": None
        }
    
    if "dislike" not in relation["relationship"]:
        relation["relationship"]["dislike"] = 0
    
    if "status" not in relation["relationship"]:
        relation["relationship"]["status"] = "空闲"
    
    context["conversation"]["conversation_info"]["time_str"] = timestamp2str(int(time.time()), week=True)
    context["conversation"]["conversation_info"]["chat_history_str"] = messages_to_str(context["conversation"]["conversation_info"]["chat_history"])
    context["conversation"]["conversation_info"]["input_messages_str"] = messages_to_str(context["conversation"]["conversation_info"]["input_messages"])

    date_str = date2str(int(time.time()))
    news = mongo.find_one("dailynews", {"date": date_str, "cid": str(character["_id"])})
    if news is None:
        context["news_str"] = ""
    else:
        context["news_str"] = news["news"]
    
    context["relation"] = relation

    return context

def context_prepare_charonly(character):
    context = {
        "character": character,
    }
    
    return context

def get_default_relation(user, character, platform):
    return {
        "uid": str(user["_id"]),
        "cid": str(character["_id"]),
        "user_info": {
            "realname": "",
            "hobbyname": "",
            "description": "在微信上认识的新朋友",
        },
        "character_info": {
            "longterm_purpose": "如果仍旧单身，则想要慢慢挑选一个合适的男友；计划去大理或者北海玩",
            "shortterm_purpose": "随便认识一下这位朋友，少量闲聊，不聊也行",
            "attitude": "略微好奇，有少量的戒备心",
            "status": "空闲"
        },
        "relationship": {
            "description": "在微信上认识的新朋友",
            "closeness": 20,
            "trustness": 20,
            "dislike": 0,
        },
    }
