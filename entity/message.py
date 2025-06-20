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

from dao.mongo import MongoDBBase


def read_top_inputmessage(to_user=None, status=None, platform=None):
    mongo = MongoDBBase()
    query = {}
    if to_user:
        query["to_user"] = to_user
    if status:
        query["status"] = status
    if platform:
        query["platform"] = platform

    result = mongo.find_one("inputmessages", query)
    return result

def read_top_inputmessages(to_user=None, status=None, platform=None, limit=16, max_handle_age=7200):
    mongo = MongoDBBase()
    query = {}
    if to_user:
        query["to_user"] = to_user
    if status:
        query["status"] = status
    if platform:
        query["platform"] = platform
    
    now = int(time.time())
    query["input_timestamp"] = {"$gt": now - max_handle_age}

    results = mongo.find_many("inputmessages", query, limit=limit)
    return results

def save_inputmessage(inputmessage):
    mongo = MongoDBBase()
    return mongo.replace_one("inputmessages", {"_id": inputmessage["_id"]}, inputmessage)

def save_outputmessage(outputmessage):
    mongo = MongoDBBase()
    return mongo.replace_one("outputmessages", {"_id": outputmessage["_id"]}, outputmessage)

def read_all_inputmessages(from_user, to_user, platform, status=None):
    mongo = MongoDBBase()
    query = {
        "platform": platform,
        "from_user": from_user,
        "to_user": to_user,
    }
    if status:
        query["status"] = status

    result = mongo.find_many("inputmessages", query)
    return result

def find_one_byid(message_id, message_type="inputmessages"):
    mongo = MongoDBBase()
    return mongo.find_one(message_type, {"_id": message_id})