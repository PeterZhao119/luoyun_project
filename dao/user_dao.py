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
from typing import Dict, List, Optional, Union, Any
from bson import ObjectId

from conf.config import CONF

class UserDAO():
    """用户模型类，提供users集合的增删改查操作"""
    
    def __init__(self, mongo_uri: str = "mongodb://" + CONF["mongodb"]["mongodb_ip"] + ":" + CONF["mongodb"]["mongodb_port"] + "/", 
                 db_name: str = CONF["mongodb"]["mongodb_name"]):
        """
        初始化User类
        
        Args:
            mongo_uri: MongoDB连接URI
            db_name: 数据库名称
        """
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection: Collection = self.db.get_collection("users")
    
    def create_indexes(self):
        """创建必要的索引"""
        # 为平台ID创建索引
        self.collection.create_index([
            ("platforms.wechat.id", 1)
        ])
        
        # 可以为其他平台创建类似的索引
        # self.collection.create_index([
        #     ("platforms.other_platform.id", 1)
        # ])
        
        # 为status字段创建索引
        self.collection.create_index([("status", 1)])
        
        # 为is_character字段创建索引
        self.collection.create_index([("is_character", 1)])
    
    def create_user(self, user_data: Dict) -> str:
        """
        创建新用户
        
        Args:
            user_data: 用户数据字典
            
        Returns:
            str: 插入的用户ID
        """
        if "_id" in user_data and isinstance(user_data["_id"], str):
            user_data["_id"] = ObjectId(user_data["_id"])
            
        result = self.collection.insert_one(user_data)
        return str(result.inserted_id)
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """
        通过ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Dict]: 用户数据或None
        """
        if not user_id:
            return None
            
        try:
            object_id = ObjectId(user_id)
        except:
            return None
            
        return self.collection.find_one({"_id": object_id})
    
    def get_user_by_platform(self, platform: str, platform_id: str) -> Optional[Dict]:
        """
        通过平台和平台ID获取用户
        
        Args:
            platform: 平台名称 (例如 "wechat")
            platform_id: 平台用户ID
            
        Returns:
            Optional[Dict]: 用户数据或None
        """
        if not platform or not platform_id:
            return None
            
        query = {f"platforms.{platform}.id": platform_id}
        return self.collection.find_one(query)
    
    def update_user(self, user_id: str, update_data: Dict) -> bool:
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            update_data: 要更新的数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            object_id = ObjectId(user_id)
        except:
            return False
            
        # 创建一个只包含要更新字段的字典
        update_fields = {"$set": update_data}
        
        result = self.collection.update_one(
            {"_id": object_id}, 
            update_fields
        )
        
        return result.modified_count > 0
    
    def update_platform_info(self, user_id: str, platform: str, 
                            platform_data: Dict) -> bool:
        """
        更新用户平台信息
        
        Args:
            user_id: 用户ID
            platform: 平台名称
            platform_data: 平台数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            object_id = ObjectId(user_id)
        except:
            return False
            
        update_fields = {f"$set": {f"platforms.{platform}": platform_data}}
        
        result = self.collection.update_one(
            {"_id": object_id},
            update_fields
        )
        
        return result.modified_count > 0
    
    def delete_user(self, user_id: str) -> bool:
        """
        删除用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            object_id = ObjectId(user_id)
        except:
            return False
            
        result = self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0
    
    def change_status(self, user_id: str, status: str) -> bool:
        """
        更改用户状态
        
        Args:
            user_id: 用户ID
            status: 新状态 (例如 "normal" 或 "stopped")
            
        Returns:
            bool: 更新是否成功
        """
        try:
            object_id = ObjectId(user_id)
        except:
            return False
            
        result = self.collection.update_one(
            {"_id": object_id},
            {"$set": {"status": status}}
        )
        
        return result.modified_count > 0
    
    def find_users(self, query: Dict = None, limit: int = 0, 
                  skip: int = 0, sort=None) -> Cursor:
        """
        查找符合条件的用户
        
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
    
    def count_users(self, query: Dict = None) -> int:
        """
        计算符合条件的用户数量
        
        Args:
            query: 查询条件
            
        Returns:
            int: 用户数量
        """
        if query is None:
            query = {}
            
        return self.collection.count_documents(query)
    
    def find_users_by_platform(self, platform: str, query: Dict = None, 
                              limit: int = 0) -> List[Dict]:
        """
        通过平台查找用户
        
        Args:
            platform: 平台名称
            query: 平台相关的查询条件
            limit: 最大返回数量
            
        Returns:
            List[Dict]: 用户列表
        """
        if query is None:
            query = {}
            
        # 构建平台查询
        platform_query = {}
        for key, value in query.items():
            platform_query[f"platforms.{platform}.{key}"] = value
            
        cursor = self.collection.find(platform_query).limit(limit) if limit > 0 else self.collection.find(platform_query)
        return list(cursor)
    
    def find_characters(self, query: Dict = None, limit: int = 0) -> List[Dict]:
        """
        查找角色用户
        
        Args:
            query: 附加查询条件
            limit: 最大返回数量
            
        Returns:
            List[Dict]: 角色用户列表
        """
        if query is None:
            query = {}
            
        # 添加角色条件
        character_query = {**query, "is_character": True}
        
        cursor = self.collection.find(character_query).limit(limit) if limit > 0 else self.collection.find(character_query)
        return list(cursor)
    
    def bulk_update_users(self, query: Dict, update: Dict) -> int:
        """
        批量更新用户
        
        Args:
            query: 查询条件
            update: 更新内容
            
        Returns:
            int: 更新的文档数量
        """
        result = self.collection.update_many(query, {"$set": update})
        return result.modified_count
    
    def upsert_user(self, query: Dict, user_data: Dict) -> str:
        """
        插入或更新用户
        
        Args:
            query: 查询条件
            user_data: 用户数据
            
        Returns:
            str: 用户ID
        """
        result = self.collection.update_one(
            query, 
            {"$set": user_data}, 
            upsert=True
        )
        
        if result.upserted_id:
            return str(result.upserted_id)
        else:
            # 获取匹配文档的ID
            user = self.collection.find_one(query, {"_id": 1})
            return str(user["_id"]) if user else None
    
    def add_platform_to_user(self, user_id: str, platform: str, 
                            platform_data: Dict) -> bool:
        """
        为用户添加平台信息
        
        Args:
            user_id: 用户ID
            platform: 平台名称
            platform_data: 平台数据
            
        Returns:
            bool: 添加是否成功
        """
        try:
            object_id = ObjectId(user_id)
        except:
            return False
            
        # 检查用户是否存在
        user = self.collection.find_one({"_id": object_id})
        if not user:
            return False
            
        # 初始化platforms字段(如果不存在)
        if "platforms" not in user:
            self.collection.update_one(
                {"_id": object_id},
                {"$set": {"platforms": {}}}
            )
            
        # 添加平台信息
        update_result = self.collection.update_one(
            {"_id": object_id},
            {"$set": {f"platforms.{platform}": platform_data}}
        )
        
        return update_result.modified_count > 0
    
    def remove_platform_from_user(self, user_id: str, platform: str) -> bool:
        """
        从用户删除平台信息
        
        Args:
            user_id: 用户ID
            platform: 平台名称
            
        Returns:
            bool: 删除是否成功
        """
        try:
            object_id = ObjectId(user_id)
        except:
            return False
            
        update_result = self.collection.update_one(
            {"_id": object_id},
            {"$unset": {f"platforms.{platform}": ""}}
        )
        
        return update_result.modified_count > 0
    
    def close(self):
        """关闭MongoDB连接"""
        self.client.close()


# 使用示例
if __name__ == "__main__":
    # 创建User实例
    user_model = UserDAO()
    
    # # 创建新用户
    # new_user = {
    #     "is_character": False,
    #     "name": "test_user",
    #     "platforms": {
    #         "wechat": {
    #             "id": "wx123456",
    #             "account": "testaccount",
    #             "nickname": "Test User"
    #         }
    #     },
    #     "status": "normal",
    #     "user_info": {
    #         "tags": ["new", "test"]
    #     }
    # }
    
    # user_id = user_model.create_user(new_user)
    # print(f"Created user with ID: {user_id}")
    
    # # 通过ID获取用户
    # user = user_model.get_user_by_id(user_id)
    # print(f"Found user: {user['name']}")
    
    # # 通过平台ID获取用户
    # platform_user = user_model.get_user_by_platform("wechat", "wx123456")
    # print(f"Found user by platform: {platform_user['name']}")

    results = user_model.find_users(query={
    }, limit=10)

    for result in results:
        print(result)
    
    # 关闭连接
    user_model.close()