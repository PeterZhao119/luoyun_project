import base64
import uuid
import re
from .context import ContextType
from .common.log import logger
from .common.tmp_dir import TmpDir
from conf.config import CONF
from .lib.client import GewechatClient
import requests
import xml.etree.ElementTree as ET

# 私聊信息示例
"""
{
    "TypeName": "AddMsg",
    "Appid": "wx_xxx",
    "Data": {
        "MsgId": 177581074,
        "FromUserName": {
            "string": "wxid_fromuser"
        },
        "ToUserName": {
            "string": "wxid_touser"
        },
        "MsgType": 49,
        "Content": {
            "string": ""
        },
        "Status": 3,
        "ImgStatus": 1,
        "ImgBuf": {
            "iLen": 0
        },
        "CreateTime": 1733410112,
        "MsgSource": "<msgsource>xx</msgsource>\n",
        "PushContent": "xxx",
        "NewMsgId": 5894648508580188926,
        "MsgSeq": 773900156
    },
    "Wxid": "wxid_gewechat_bot"  // 使用gewechat登录的机器人wxid
}
"""

# 群聊信息示例
"""
{
    "TypeName": "AddMsg",
    "Appid": "wx_xxx",
    "Data": {
        "MsgId": 585326344,
        "FromUserName": {
            "string": "xxx@chatroom"
        },
        "ToUserName": {
            "string": "wxid_gewechat_bot" // 接收到此消息的wxid, 即使用gewechat登录的机器人wxid
        },
        "MsgType": 1,
        "Content": {
            "string": "wxid_xxx:\n@name msg_content" // 发送消息人的wxid和消息内容(包含@name)
        },
        "Status": 3,
        "ImgStatus": 1,
        "ImgBuf": {
            "iLen": 0
        },
        "CreateTime": 1733447040,
        "MsgSource": "<msgsource>\n\t<atuserlist><![CDATA[,wxid_wvp31dkffyml19]]></atuserlist>\n\t<pua>1</pua>\n\t<silence>0</silence>\n\t<membercount>3</membercount>\n\t<signature>V1_cqxXBat9|v1_cqxXBat9</signature>\n\t<tmp_node>\n\t\t<publisher-id></publisher-id>\n\t</tmp_node>\n</msgsource>\n",
        "PushContent": "xxx在群聊中@了你",
        "NewMsgId": 8449132831264840264,
        "MsgSeq": 773900177
    },
    "Wxid": "wxid_gewechat_bot"  // 使用gewechat登录的机器人wxid
}
"""

# 群邀请消息示例
"""
{
    "TypeName": "AddMsg",
    "Appid": "wx_xxx",
    "Data": {
        "MsgId": 488566999,
        "FromUserName": {
            "string": "xxx@chatroom"
        },
        "ToUserName": {
            "string": "wxid_gewechat_bot"
        },
        "MsgType": 10002,
        "Content": {
            "string": "53760920521@chatroom:\n<sysmsg type=\"sysmsgtemplate\">\n\t<sysmsgtemplate>\n\t\t<content_template type=\"tmpl_type_profile\">\n\t\t\t<plain><![CDATA[]]></plain>\n\t\t\t<template><![CDATA[\"$username$\"邀请\"$names$\"加入了群聊]]></template>\n\t\t\t<link_list>\n\t\t\t\t<link name=\"username\" type=\"link_profile\">\n\t\t\t\t\t<memberlist>\n\t\t\t\t\t\t<member>\n\t\t\t\t\t\t\t<username><![CDATA[wxid_eaclcf34ny6221]]></username>\n\t\t\t\t\t\t\t<nickname><![CDATA[刘贺]]></nickname>\n\t\t\t\t\t\t</member>\n\t\t\t\t\t</memberlist>\n\t\t\t\t</link>\n\t\t\t\t<link name=\"names\" type=\"link_profile\">\n\t\t\t\t\t<memberlist>\n\t\t\t\t\t\t<member>\n\t\t\t\t\t\t\t<username><![CDATA[wxid_mmwc3zzkfcl922]]></username>\n\t\t\t\t\t\t\t<nickname><![CDATA[郑德娟]]></nickname>\n\t\t\t\t\t\t</member>\n\t\t\t\t\t</memberlist>\n\t\t\t\t\t<separator><![CDATA[、]]></separator>\n\t\t\t\t</link>\n\t\t\t</link_list>\n\t\t</content_template>\n\t</sysmsgtemplate>\n</sysmsg>\n"
        },
        "Status": 4,
        "ImgStatus": 1,
        "ImgBuf": {
            "iLen": 0
        },
        "CreateTime": 1736820013,
        "MsgSource": "<msgsource>\n\t<tmp_node>\n\t\t<publisher-id></publisher-id>\n\t</tmp_node>\n</msgsource>\n",
        "NewMsgId": 5407479395895269893,
        "MsgSeq": 821038175
    },
    "Wxid": "wxid_gewechat_bot"
}
"""

"""
{
    "TypeName": "ModContacts",
    "Appid": "wx_xxx",
    "Data": {
        "UserName": {
            "string": "xxx@chatroom"
        },
        "NickName": {
            "string": "测试2"
        },
        "PyInitial": {
            "string": "CS2"
        },
        "QuanPin": {
            "string": "ceshi2"
        },
        "Sex": 0,
        "ImgBuf": {
            "iLen": 0
        },
        "BitMask": 4294967295,
        "BitVal": 2,
        "ImgFlag": 1,
        "Remark": {},
        "RemarkPyinitial": {},
        "RemarkQuanPin": {},
        "ContactType": 0,
        "RoomInfoCount": 0,
        "DomainList": [
            {}
        ],
        "ChatRoomNotify": 1,
        "AddContactScene": 0,
        "PersonalCard": 0,
        "HasWeiXinHdHeadImg": 0,
        "VerifyFlag": 0,
        "Level": 0,
        "Source": 0,
        "ChatRoomOwner": "wxid_xxx",
        "WeiboFlag": 0,
        "AlbumStyle": 0,
        "AlbumFlag": 0,
        "SnsUserInfo": {
            "SnsFlag": 0,
            "SnsBgobjectId": 0,
            "SnsFlagEx": 0
        },
        "CustomizedInfo": {
            "BrandFlag": 0
        },
        "AdditionalContactList": {
            "LinkedinContactItem": {}
        },
        "ChatroomMaxCount": 10008,
        "DeleteFlag": 0,
        "Description": "\b\u0004\u0012\u001c\n\u0013wxid_xxx0\u0001@\u0000\u0001\u0000\u0012\u001c\n\u0013wxid_xxx0\u0001@\u0000\u0001\u0000\u0012\u001c\n\u0013wxid_xxx0\u0001@\u0000\u0001\u0000\u0012\u001c\n\u0013wxid_xxx0\u0001@\u0000\u0001\u0000\u0018\u0001\"\u0000(\u00008\u0000",
        "ChatroomStatus": 5,
        "Extflag": 0,
        "ChatRoomBusinessType": 0
    },
    "Wxid": "wxid_xxx"
}
"""

# 群聊中移除用户示例
"""
{
    "UserName": {
        "string": "xxx@chatroom"
    },
    "NickName": {
        "string": "AITestGroup"
    },
    "PyInitial": {
        "string": "AITESTGROUP"
    },
    "QuanPin": {
        "string": "AITestGroup"
    },
    "Sex": 0,
    "ImgBuf": {
        "iLen": 0
    },
    "BitMask": 4294967295,
    "BitVal": 2,
    "ImgFlag": 1,
    "Remark": {},
    "RemarkPyinitial": {},
    "RemarkQuanPin": {},
    "ContactType": 0,
    "RoomInfoCount": 0,
    "DomainList": [
        {}
    ],
    "ChatRoomNotify": 1,
    "AddContactScene": 0,
    "PersonalCard": 0,
    "HasWeiXinHdHeadImg": 0,
    "VerifyFlag": 0,
    "Level": 0,
    "Source": 0,
    "ChatRoomOwner": "wxid_xxx",
    "WeiboFlag": 0,
    "AlbumStyle": 0,
    "AlbumFlag": 0,
    "SnsUserInfo": {
        "SnsFlag": 0,
        "SnsBgobjectId": 0,
        "SnsFlagEx": 0
    },
    "CustomizedInfo": {
        "BrandFlag": 0
    },
    "AdditionalContactList": {
        "LinkedinContactItem": {}
    },
    "ChatroomMaxCount": 10037,
    "DeleteFlag": 0,
    "Description": "\b\u0002\u0012\u001c\n\u0013wxid_eacxxxx\u0001@\u0000�\u0001\u0000\u0012\u001c\n\u0013wxid_xxx\u0001@\u0000�\u0001\u0000\u0018\u0001\"\u0000(\u00008\u0000",
    "ChatroomStatus": 4,
    "Extflag": 0,
    "ChatRoomBusinessType": 0
}
"""

# 群聊中移除用户示例
"""
{
    "TypeName": "ModContacts",
    "Appid": "wx_xxx",
    "Data": {
        "UserName": {
            "string": "xxx@chatroom"
        },
        "NickName": {
            "string": "测试2"
        },
        "PyInitial": {
            "string": "CS2"
        },
        "QuanPin": {
            "string": "ceshi2"
        },
        "Sex": 0,
        "ImgBuf": {
            "iLen": 0
        },
        "BitMask": 4294967295,
        "BitVal": 2,
        "ImgFlag": 2,
        "Remark": {},
        "RemarkPyinitial": {},
        "RemarkQuanPin": {},
        "ContactType": 0,
        "RoomInfoCount": 0,
        "DomainList": [
            {}
        ],
        "ChatRoomNotify": 1,
        "AddContactScene": 0,
        "PersonalCard": 0,
        "HasWeiXinHdHeadImg": 0,
        "VerifyFlag": 0,
        "Level": 0,
        "Source": 0,
        "ChatRoomOwner": "wxid_xxx",
        "WeiboFlag": 0,
        "AlbumStyle": 0,
        "AlbumFlag": 0,
        "SnsUserInfo": {
            "SnsFlag": 0,
            "SnsBgobjectId": 0,
            "SnsFlagEx": 0
        },
        "SmallHeadImgUrl": "https://wx.qlogo.cn/mmcrhead/xxx/0",
        "CustomizedInfo": {
            "BrandFlag": 0
        },
        "AdditionalContactList": {
            "LinkedinContactItem": {}
        },
        "ChatroomMaxCount": 10007,
        "DeleteFlag": 0,
        "Description": "\b\u0003\u0012\u001c\n\u0013wxid_xxx0\u0001@\u0000\u0001\u0000\u0012\u001c\n\u0013wxid_xxx0\u0001@\u0000\u0001\u0000\u0012\u001c\n\u0013wxid_xxx0\u0001@\u0000\u0001\u0000\u0018\u0001\"\u0000(\u00008\u0000",
        "ChatroomStatus": 5,
        "Extflag": 0,
        "ChatRoomBusinessType": 0
    },
    "Wxid": "wxid_xxx"
}
"""

class GeWeChatMessage:
    """GeWeChat message class"""
    def __init__(self, msg, client=None):
        self.msg = msg
        self.msg_data = msg.get("Data", {})
        self.msg_id = self.msg_data.get('NewMsgId', 0)
        self.is_group = '@chatroom' in self.msg_data.get('FromUserName', {}).get('string', '')
        
        gewechat_config = CONF.get("dev", {}).get("gewechat", {})
        self.app_id = gewechat_config.get("gewechat_app_id")
        
        self.from_user_id = self.msg_data.get('FromUserName', {}).get('string', '')
        self.to_user_id = self.msg_data.get('ToUserName', {}).get('string', '')
        self.ctype = ContextType.UNKNOWN
        self.content = ""
        self.client = client
        
        # Other user is the counterpart
        self.other_user_id = self.to_user_id if self.from_user_id == self.msg.get('Wxid') else self.from_user_id
        self.other_user_nickname = self.other_user_id
        
        # Actual user is who actually sent the message (in group chats)
        self.actual_user_id = self.other_user_id
        self.actual_user_nickname = self.other_user_id
        
        # For group messages, we need to parse the content to get the actual sender
        if self.is_group:
            content = self.msg_data.get('Content', {}).get('string', '')
            if ':' in content:
                parts = content.split(':', 1)
                self.actual_user_id = parts[0].strip()
                self.content = parts[1].strip() if len(parts) > 1 else ""
            else:
                self.content = content
        else:
            self.content = self.msg_data.get('Content', {}).get('string', '')
        
        # Chat room name (for group chats)
        self.chatroom_name = self.from_user_id if self.is_group else ""
        
        # Is this a message from myself?
        self.my_msg = self.msg.get('Wxid') == self.from_user_id
    
    def is_valid(self):
        """Check if this message is valid and should be processed"""
        return True
