# -*- coding: utf-8 -*-
import os
import time
import requests
import json

import sys
sys.path.append(".")

import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

from conf.config import CONF

auth = CONF["ecloud"]["Authorization"]
host = "http://125.122.152.142:9899"

class Ecloud_API():
    @staticmethod
    def getContact(wcId, target_user_alias):
        wid = CONF["ecloud"]["wId"][target_user_alias]
        data = {
            "wId": wid,
            "wcId": wcId
        }
        logger.info(data)
        resp = requests.post(
            url=host+"/getContact",
            json=data,
            headers={
                "Authorization": auth,
                "Content-Type": "application/json"
            }
        )

        resp_json = json.loads(resp.content.decode("utf-8"))
        return resp_json
    
    @staticmethod
    def sendText(data):
        resp = requests.post(
            url=host+"/sendText",
            json=data,
            headers={
                "Authorization": auth,
                "Content-Type": "application/json"
            }
        )

        resp_json = json.loads(resp.content.decode("utf-8"))
        return resp_json
    
    @staticmethod
    def sendVoice(data):
        resp = requests.post(
            url=host+"/sendVoice",
            json=data,
            headers={
                "Authorization": auth,
                "Content-Type": "application/json"
            }
        )

        resp_json = json.loads(resp.content.decode("utf-8"))
        return resp_json
    
    @staticmethod
    def sendImage(data):
        resp = requests.post(
            url=host+"/sendImage2",
            json=data,
            headers={
                "Authorization": auth,
                "Content-Type": "application/json"
            }
        )

        resp_json = json.loads(resp.content.decode("utf-8"))
        return resp_json
    
    @staticmethod
    def getMsgVoice(data):
        resp = requests.post(
            url=host+"/getMsgVoice",
            json=data,
            headers={
                "Authorization": auth,
                "Content-Type": "application/json"
            }
        )

        resp_json = json.loads(resp.content.decode("utf-8"))
        return resp_json
    
    @staticmethod
    def getMsgImg(data):
        resp = requests.post(
            url=host+"/getMsgImg",
            json=data,
            headers={
                "Authorization": auth,
                "Content-Type": "application/json"
            }
        )

        resp_json = json.loads(resp.content.decode("utf-8"))
        return resp_json
    
    @staticmethod
    def snsSendImage(data):
        resp = requests.post(
            url=host+"/snsSendImage",
            json=data,
            headers={
                "Authorization": auth,
                "Content-Type": "application/json"
            }
        )

        resp_json = json.loads(resp.content.decode("utf-8"))
        return resp_json

if __name__ == "__main__":
    target_user_alias = "luoyun"
    data = {
        "wId": CONF["ecloud"]["wId"][target_user_alias],
        "wcId": "LeanInWind",
        # "content": "/home/ecs-user/luoyun/framework/tool/text2voice/test.silk",
        "content": "https://banyou-live.oss-cn-beijing.aliyuncs.com/test.silk?x-oss-date=20250519T171906Z&x-oss-expires=300&x-oss-signature-version=OSS4-HMAC-SHA256&x-oss-credential=LTAI5t5uQzkR9g7FCU5YLAwR%2F20250519%2Fcn-beijing%2Foss%2Faliyun_v4_request&x-oss-signature=02b3f518c2d588f61f2c8d2a0a9107628793ab254f5c503270cc2d3cc23ac6e7",
        "length": 24
    }
    resp_json = Ecloud_API.sendVoice(data)
    print(resp_json)
