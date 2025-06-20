import os
import time

import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

import sys
sys.path.append(".")

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from typing import Dict, List, Optional, Union, Any, Tuple
from bson import ObjectId

from conf.config import CONF


class ConversationDAO():
    """会话模型类，提供conversations集合的增删改查操作"""
    
    def __init__(self, mongo_uri: str = "mongodb://" + CONF["mongodb"]["mongodb_ip"] + ":" + CONF["mongodb"]["mongodb_port"] + "/", 
                 db_name: str = CONF["mongodb"]["mongodb_name"]):
        """
        初始化Conversation类
        
        Args:
            mongo_uri: MongoDB连接URI
            db_name: 数据库名称
        """
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection: Collection = self.db.conversations
    
    def create_indexes(self):
        """创建必要的索引"""
        # 为平台创建索引
        self.collection.create_index([("platform", 1)])
        
        # 为群聊名称创建索引
        self.collection.create_index([("chatroom_name", 1)])
        
        # 为talkers.id创建索引，支持按参与者查询
        self.collection.create_index([("talkers.id", 1)])
        
        # 创建组合索引，优化单聊查询
        self.collection.create_index([
            ("platform", 1),
            ("chatroom_name", 1),
            ("talkers.id", 1)
        ])
    
    def create_conversation(self, conversation_data: Dict) -> str:
        """
        创建新会话
        
        Args:
            conversation_data: 会话数据字典
            
        Returns:
            str: 插入的会话ID
        """
        if "_id" in conversation_data and isinstance(conversation_data["_id"], str):
            conversation_data["_id"] = ObjectId(conversation_data["_id"])
            
        result = self.collection.insert_one(conversation_data)
        return str(result.inserted_id)
    
    def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict]:
        """
        通过ID获取会话
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            Optional[Dict]: 会话数据或None
        """
        if not conversation_id:
            return None
            
        try:
            object_id = ObjectId(conversation_id)
        except:
            return None
            
        return self.collection.find_one({"_id": object_id})
    
    def get_private_conversation(self, platform: str, user_id1: str, user_id2: str) -> Optional[Dict]:
        """
        获取两个用户之间的单聊会话
        
        Args:
            platform: 平台名称
            user_id1: 第一个用户ID
            user_id2: 第二个用户ID
            
        Returns:
            Optional[Dict]: 会话数据或None
        """
        if not platform or not user_id1 or not user_id2:
            return None
        
        # 构建查询条件：平台匹配，不是群聊，且两个用户都在talkers中
        query = {
            "platform": platform,
            "chatroom_name": None,
            "talkers.id": {"$all": [user_id1, user_id2]},
            # 确保只有这两个用户（即talkers数组长度为2）
            "$where": "this.talkers.length === 2"
        }
        
        return self.collection.find_one(query)
    
    def get_group_conversation(self, platform: str, chatroom_name: str) -> Optional[Dict]:
        """
        获取群聊会话
        
        Args:
            platform: 平台名称
            chatroom_name: 群聊名称
            
        Returns:
            Optional[Dict]: 会话数据或None
        """
        if not platform or not chatroom_name:
            return None
        
        query = {
            "platform": platform,
            "chatroom_name": chatroom_name
        }
        
        return self.collection.find_one(query)
    
    def update_conversation(self, conversation_id: str, update_data: Dict) -> bool:
        """
        更新会话信息
        
        Args:
            conversation_id: 会话ID
            update_data: 要更新的数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            object_id = ObjectId(conversation_id)
        except:
            return False
        
        # 创建一个只包含要更新字段的字典
        update_fields = {"$set": update_data}
        
        result = self.collection.update_one(
            {"_id": object_id}, 
            update_fields
        )
        
        return result.modified_count > 0
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除会话
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            object_id = ObjectId(conversation_id)
        except:
            return False
            
        result = self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0
    
    def find_conversations(self, query: Dict = None, limit: int = 0, 
                          skip: int = 0, sort=None) -> Cursor:
        """
        查找符合条件的会话
        
        Args:
            query: 查询条件
            limit: 最大返回数量
            skip: 跳过的文档数
            sort: 排序字段
            
        Returns:
            Cursor: MongoDB游标
        """
        if query is None:
            query = {}
            
        cursor = self.collection.find(query)
        
        if skip > 0:
            cursor = cursor.skip(skip)
            
        if limit > 0:
            cursor = cursor.limit(limit)
            
        if sort:
            cursor = cursor.sort(sort)
            
        return list(cursor)
    
    def find_conversations_by_user(self, user_id: str, platform: Optional[str] = None,
                                  include_groups: bool = True) -> List[Dict]:
        """
        查找用户参与的所有会话
        
        Args:
            user_id: 用户ID
            platform: 可选平台过滤
            include_groups: 是否包含群聊
            
        Returns:
            List[Dict]: 会话列表
        """
        query = {"talkers.id": user_id}
        
        if platform:
            query["platform"] = platform
            
        if not include_groups:
            query["chatroom_name"] = None
            
        cursor = self.collection.find(query)
        return list(cursor)
    
    def add_user_to_conversation(self, conversation_id: str, 
                                user_id: str, nickname: str) -> bool:
        """
        向会话添加用户
        
        Args:
            conversation_id: 会话ID
            user_id: 用户ID
            nickname: 用户在会话中的昵称
            
        Returns:
            bool: 添加是否成功
        """
        try:
            object_id = ObjectId(conversation_id)
        except:
            return False
            
        # 检查用户是否已在会话中
        conversation = self.collection.find_one({
            "_id": object_id,
            "talkers.id": user_id
        })
        
        if conversation:
            # 用户已在会话中
            return False
            
        # 添加新用户到talkers数组
        result = self.collection.update_one(
            {"_id": object_id},
            {"$push": {"talkers": {"id": user_id, "nickname": nickname}}}
        )
        
        return result.modified_count > 0
    
    def remove_user_from_conversation(self, conversation_id: str, user_id: str) -> bool:
        """
        从会话移除用户
        
        Args:
            conversation_id: 会话ID
            user_id: 用户ID
            
        Returns:
            bool: 移除是否成功
        """
        try:
            object_id = ObjectId(conversation_id)
        except:
            return False
            
        result = self.collection.update_one(
            {"_id": object_id},
            {"$pull": {"talkers": {"id": user_id}}}
        )
        
        return result.modified_count > 0
    
    def update_user_nickname(self, conversation_id: str, 
                            user_id: str, new_nickname: str) -> bool:
        """
        更新用户在会话中的昵称
        
        Args:
            conversation_id: 会话ID
            user_id: 用户ID
            new_nickname: 新昵称
            
        Returns:
            bool: 更新是否成功
        """
        try:
            object_id = ObjectId(conversation_id)
        except:
            return False
            
        result = self.collection.update_one(
            {
                "_id": object_id,
                "talkers.id": user_id
            },
            {"$set": {"talkers.$.nickname": new_nickname}}
        )
        
        return result.modified_count > 0
    
    def rename_group(self, conversation_id: str, new_name: str) -> bool:
        """
        重命名群聊
        
        Args:
            conversation_id: 会话ID
            new_name: 新群名称
            
        Returns:
            bool: 重命名是否成功
        """
        try:
            object_id = ObjectId(conversation_id)
        except:
            return False
            
        # 验证这是一个群聊
        conversation = self.collection.find_one({
            "_id": object_id,
            "chatroom_name": {"$ne": None}
        })
        
        if not conversation:
            return False
            
        result = self.collection.update_one(
            {"_id": object_id},
            {"$set": {"chatroom_name": new_name}}
        )
        
        return result.modified_count > 0
    
    def get_or_create_private_conversation(self, platform: str, 
                                          user_id1: str, nickname1: str,
                                          user_id2: str, nickname2: str) -> Tuple[str, bool]:
        """
        获取或创建单聊会话
        
        Args:
            platform: 平台
            user_id1: 第一个用户ID
            nickname1: 第一个用户昵称
            user_id2: 第二个用户ID
            nickname2: 第二个用户昵称
            
        Returns:
            Tuple[str, bool]: 会话ID和是否新创建的标志
        """
        # 先尝试查找现有会话
        existing = self.get_private_conversation(platform, user_id1, user_id2)
        
        if existing:
            return str(existing["_id"]), False
            
        # 创建新会话
        new_conversation = {
            "chatroom_name": None,
            "talkers": [
                {"id": user_id1, "nickname": nickname1},
                {"id": user_id2, "nickname": nickname2}
            ],
            "platform": platform,
            "conversation_info": {}
        }
        
        conversation_id = self.create_conversation(new_conversation)
        return conversation_id, True
    
    def get_or_create_group_conversation(self, platform: str, 
                                        chatroom_name: str,
                                        initial_talkers: List[Dict] = None) -> Tuple[str, bool]:
        """
        获取或创建群聊会话
        
        Args:
            platform: 平台
            chatroom_name: 群聊名称
            initial_talkers: 初始参与者列表 [{"id": "xxx", "nickname": "xxx"}, ...]
            
        Returns:
            Tuple[str, bool]: 会话ID和是否新创建的标志
        """
        # 先尝试查找现有群聊
        existing = self.get_group_conversation(platform, chatroom_name)
        
        if existing:
            return str(existing["_id"]), False
            
        # 创建新群聊
        new_conversation = {
            "chatroom_name": chatroom_name,
            "talkers": initial_talkers or [],
            "platform": platform,
            "conversation_info": {}
        }
        
        conversation_id = self.create_conversation(new_conversation)
        return conversation_id, True
    
    def update_conversation_info(self, conversation_id: str, info_data: Dict) -> bool:
        """
        更新会话算法侧信息
        
        Args:
            conversation_id: 会话ID
            info_data: 算法侧信息
            
        Returns:
            bool: 更新是否成功
        """
        try:
            object_id = ObjectId(conversation_id)
        except:
            return False
            
        result = self.collection.update_one(
            {"_id": object_id},
            {"$set": {"conversation_info": info_data}}
        )
        
        return result.modified_count > 0
    
    def count_conversations(self, query: Dict = None) -> int:
        """
        计算符合条件的会话数量
        
        Args:
            query: 查询条件
            
        Returns:
            int: 会话数量
        """
        if query is None:
            query = {}
            
        return self.collection.count_documents(query)
    
    def close(self):
        """关闭MongoDB连接"""
        self.client.close()


# 使用示例
if __name__ == "__main__":
    # 创建Conversation实例
    conversation_model = ConversationDAO()
    
    conversations = conversation_model.find_conversations(query={
        "conversation_info.future.action": {
            "$ne": None,      # 值不等于null
            "$exists": True   # 字段必须存在
        },
        "talkers.nickname": "不辣的皮皮"
    })

    for conversation in conversations:
        print(conversation)