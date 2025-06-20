"""
MongoDB Vector Database Library
包含基础数据库操作和向量检索功能
"""
import os
import time

import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

import sys
sys.path.append(".")

import pymongo
from pymongo import MongoClient
from typing import Dict, List, Any, Optional, Union, Tuple
import numpy as np
from bson import ObjectId

from conf.config import CONF

class MongoDBBase:
    """MongoDB基础类"""
    
    def __init__(self, connection_string: str = "mongodb://" + CONF["mongodb"]["mongodb_ip"] + ":" + CONF["mongodb"]["mongodb_port"] + "/", 
                 db_name: str = CONF["mongodb"]["mongodb_name"]):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        
    def get_collection(self, collection_name: str):
        """获取指定集合"""
        return self.db[collection_name]
    
    def insert_one(self, collection_name: str, document: Dict) -> str:
        """插入单个文档"""
        result = self.db[collection_name].insert_one(document)
        return str(result.inserted_id)
    
    def insert_many(self, collection_name: str, documents: List[Dict]) -> List[str]:
        """插入多个文档"""
        result = self.db[collection_name].insert_many(documents)
        return [str(id) for id in result.inserted_ids]
    
    def find_one(self, collection_name: str, query: Dict) -> Dict:
        """查找单个文档"""
        return self.db[collection_name].find_one(query)
    
    def find_many(self, collection_name: str, query: Dict, limit: int = 0) -> List[Dict]:
        """查找多个文档"""
        cursor = self.db[collection_name].find(query)
        if limit > 0:
            cursor = cursor.limit(limit)
        return list(cursor)
    
    def update_one(self, collection_name: str, query: Dict, update: Dict) -> int:
        """更新单个文档"""
        result = self.db[collection_name].update_one(query, update)
        return result.modified_count
    
    def update_many(self, collection_name: str, query: Dict, update: Dict) -> int:
        """更新多个文档"""
        result = self.db[collection_name].update_many(query, update)
        return result.modified_count
    
    def replace_one(self, collection_name: str, query: Dict, update: Dict) -> int:
        """替换单个文档"""
        result = self.db[collection_name].replace_one(query, update)
        return result.modified_count
    
    def delete_one(self, collection_name: str, query: Dict) -> int:
        """删除单个文档"""
        result = self.db[collection_name].delete_one(query)
        return result.deleted_count
    
    def delete_many(self, collection_name: str, query: Dict) -> int:
        """删除多个文档"""
        result = self.db[collection_name].delete_many(query)
        return result.deleted_count
    
    def count_documents(self, collection_name: str, query: Dict = None) -> int:
        """计算文档数量"""
        if query is None:
            query = {}
        return self.db[collection_name].count_documents(query)
    
    def create_index(self, collection_name: str, keys, **kwargs):
        """创建索引"""
        return self.db[collection_name].create_index(keys, **kwargs)
    
    def drop_collection(self, collection_name: str):
        """删除集合"""
        self.db.drop_collection(collection_name)
    
    def list_collections(self) -> List[str]:
        """列出所有集合"""
        return self.db.list_collection_names()
    
    def aggregate(self, collection_name: str, pipeline: List[Dict]) -> List[Dict]:
        """聚合查询"""
        return list(self.db[collection_name].aggregate(pipeline))
    
    def close(self):
        """关闭连接"""
        self.client.close()
    
    # 向量库
    def create_vector_collection(self, collection_name: str, create_indexes: bool = True) -> None:
        """
        创建向量集合并添加索引
        """
        # 检查集合是否存在，不存在则创建
        if collection_name not in self.db.list_collection_names():
            self.db.create_collection(collection_name)
        
        # 创建索引以加速查询
        if create_indexes:
            collection = self.db[collection_name]
            # 为文本字段创建索引
            collection.create_index("key")
            collection.create_index("value")
            # 为向量字段创建索引 (MongoDB 5.0+支持向量索引)
            # 如果使用MongoDB 5.0+并支持向量索引，可以添加向量索引
            # collection.create_index([("key_embedding", "vector")])
            # collection.create_index([("value_embedding", "vector")])
    
    def insert_vector(self, collection_name: str, key: str, value: str, 
                     key_embedding: List[float], value_embedding: List[float],
                     metadata: Dict[str, Any] = None) -> str:
        """
        插入向量数据
        返回插入文档的ID
        """
        if metadata is None:
            metadata = {}
        
        # 创建文档
        document = {
            "key": key,
            "value": value,
            "key_embedding": key_embedding,
            "value_embedding": value_embedding,
            "metadata": metadata
        }
        
        # 插入文档并返回ID
        result = self.db[collection_name].insert_one(document)
        return str(result.inserted_id)
    
    def get_vector_by_id(self, collection_name: str, doc_id: str) -> Dict:
        """
        通过ID获取向量文档
        """
        result = self.db[collection_name].find_one({"_id": ObjectId(doc_id)})
        return result
    
    def get_vectors_by_text(self, collection_name: str, field: str, text: str) -> List[Dict]:
        """
        通过文本内容获取向量文档
        field: "key" 或 "value"
        """
        if field not in ["key", "value"]:
            raise ValueError("field must be 'key' or 'value'")
        
        # 使用正则表达式进行部分匹配
        query = {field: {"$regex": text, "$options": "i"}}
        results = list(self.db[collection_name].find(query))
        return results
    
    def update_vector(self, collection_name: str, doc_id: str, 
                     key: str = None, value: str = None,
                     key_embedding: List[float] = None, 
                     value_embedding: List[float] = None,
                     metadata: Dict[str, Any] = None) -> bool:
        """
        更新向量文档
        只更新提供的字段
        返回是否成功更新
        """
        update_fields = {}
        
        if key is not None:
            update_fields["key"] = key
        if value is not None:
            update_fields["value"] = value
        if key_embedding is not None:
            update_fields["key_embedding"] = key_embedding
        if value_embedding is not None:
            update_fields["value_embedding"] = value_embedding
        if metadata is not None:
            update_fields["metadata"] = metadata
        
        if not update_fields:
            return False
        
        result = self.db[collection_name].update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": update_fields}
        )
        
        return result.modified_count > 0
    
    def update_metadata(self, collection_name: str, doc_id: str, 
                       metadata_updates: Dict[str, Any]) -> bool:
        """
        更新文档的metadata字段
        可以只更新特定的metadata键
        """
        # 构建更新操作
        update_dict = {}
        for key, value in metadata_updates.items():
            update_dict[f"metadata.{key}"] = value
        
        result = self.db[collection_name].update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": update_dict}
        )
        
        return result.modified_count > 0
    
    def delete_vector(self, collection_name: str, doc_id: str) -> bool:
        """
        删除向量文档
        返回是否成功删除
        """
        result = self.db[collection_name].delete_one({"_id": ObjectId(doc_id)})
        return result.deleted_count > 0
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        dot_product = np.dot(vec1, vec2)
        norm_a = np.linalg.norm(vec1)
        norm_b = np.linalg.norm(vec2)
        
        # 避免除以0
        if norm_a == 0 or norm_b == 0:
            return 0
            
        return dot_product / (norm_a * norm_b)
    
    def vector_search(self, collection_name: str, 
                     query_embedding: List[float],
                     embedding_field: str = "key_embedding",
                     metadata_filters: Dict[str, Any] = None,
                     top_k: int = 10,
                     similarity_threshold: float = 0.0) -> List[Dict]:
        """
        向量相似度搜索
        embedding_field: "key_embedding" 或 "value_embedding"
        metadata_filters: 元数据过滤条件，格式为 {"字段名": 值}
        top_k: 返回的最大结果数量
        similarity_threshold: 相似度阈值，只返回相似度大于此值的结果
        """
        if embedding_field not in ["key_embedding", "value_embedding"]:
            raise ValueError("embedding_field must be 'key_embedding' or 'value_embedding'")
        
        # 构建查询条件
        query = {}
        if metadata_filters:
            for key, value in metadata_filters.items():
                query[f"metadata.{key}"] = value
        
        # 获取所有符合条件的文档
        cursor = self.db[collection_name].find(query)
        
        # 计算相似度并排序
        results = []
        for doc in cursor:
            if embedding_field in doc and isinstance(doc[embedding_field], list):
                similarity = self._cosine_similarity(query_embedding, doc[embedding_field])
                
                if similarity >= similarity_threshold:
                    # 添加相似度到结果中
                    doc_with_score = dict(doc)
                    doc_with_score["similarity"] = similarity
                    results.append(doc_with_score)
        
        # 按相似度降序排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 返回前top_k个结果
        return results[:top_k]
    
    def combined_search(self, collection_name: str,
                       text_query: str = None, text_field: str = "key",
                       query_embedding: List[float] = None, embedding_field: str = "key_embedding",
                       metadata_filters: Dict[str, Any] = None,
                       top_k: int = 10,
                       similarity_threshold: float = 0.0) -> List[Dict]:
        """
        组合搜索：支持文本查询和向量查询的结合
        """
        # 构建基础查询条件
        query = {}
        
        # 添加文本查询条件
        if text_query and text_field in ["key", "value"]:
            query[text_field] = {"$regex": text_query, "$options": "i"}
        
        # 添加元数据过滤条件
        if metadata_filters:
            for key, value in metadata_filters.items():
                query[f"metadata.{key}"] = value
        
        # 执行查询
        cursor = self.db[collection_name].find(query)
        
        # 如果有向量查询
        if query_embedding and embedding_field in ["key_embedding", "value_embedding"]:
            # 计算相似度并排序
            results = []
            for doc in cursor:
                if embedding_field in doc and isinstance(doc[embedding_field], list):
                    similarity = self._cosine_similarity(query_embedding, doc[embedding_field])
                    
                    if similarity >= similarity_threshold:
                        # 添加相似度到结果中
                        doc_with_score = dict(doc)
                        doc_with_score["similarity"] = similarity
                        results.append(doc_with_score)
            
            # 按相似度降序排序
            results.sort(key=lambda x: x["similarity"], reverse=True)
            
            # 返回前top_k个结果
            return results[:top_k]
        else:
            # 只有文本和元数据过滤，没有向量查询
            return list(cursor.limit(top_k))


class VectorDB(MongoDBBase):
    """向量数据库类，继承自MongoDBBase"""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017/", 
                 db_name: str = "vector_db", vector_dimension: int = 1536):
        super().__init__(connection_string, db_name)
        self.vector_dimension = vector_dimension
    
    def create_vector_collection(self, collection_name: str, vector_field: str = "vector"):
        """创建向量集合并建立索引"""
        if collection_name not in self.list_collections():
            self.db.create_collection(collection_name)
            
        # 创建向量索引
        index_config = {
            "mappings": {
                "dynamic": True,
                "fields": {
                    vector_field: {
                        "dimensions": self.vector_dimension,
                        "similarity": "cosine",
                        "type": "knnVector"
                    }
                }
            }
        }
        
        self.db.command({
            "createIndexes": collection_name,
            "indexes": [{
                "name": f"{vector_field}_vector_index",
                "key": {vector_field: "vector"},
                "weights": index_config
            }]
        })
        
    def insert_vector_document(self, collection_name: str, vector: List[float], 
                               metadata: Dict = None, vector_field: str = "vector") -> str:
        """插入向量文档"""
        if metadata is None:
            metadata = {}
            
        document = {
            vector_field: vector,
            **metadata
        }
        
        return self.insert_one(collection_name, document)
    
    def insert_many_vector_documents(self, collection_name: str, vectors: List[List[float]], 
                                    metadata_list: List[Dict] = None, 
                                    vector_field: str = "vector") -> List[str]:
        """批量插入向量文档"""
        if metadata_list is None:
            metadata_list = [{} for _ in range(len(vectors))]
        
        if len(vectors) != len(metadata_list):
            raise ValueError("向量列表和元数据列表长度不一致")
            
        documents = [
            {vector_field: vector, **metadata}
            for vector, metadata in zip(vectors, metadata_list)
        ]
        
        return self.insert_many(collection_name, documents)
    
    def vector_search(self, collection_name: str, query_vector: List[float], 
                     k: int = 10, vector_field: str = "vector", 
                     filter_query: Dict = None) -> List[Dict]:
        """向量相似度搜索"""
        if filter_query is None:
            filter_query = {}
            
        pipeline = [
            {
                "$search": {
                    "index": f"{vector_field}_vector_index",
                    "knnBeta": {
                        "vector": query_vector,
                        "path": vector_field,
                        "k": k,
                        "filter": filter_query if filter_query else None
                    }
                }
            },
            {
                "$project": {
                    "score": {"$meta": "searchScore"},
                    "_id": 1,
                    vector_field: 1,
                    "metadata": "$$ROOT"
                }
            }
        ]
        
        if filter_query:
            pipeline.append({"$match": filter_query})
            
        return self.aggregate(collection_name, pipeline)
    
    def hybrid_search(self, collection_name: str, query_vector: List[float], 
                     text_query: str, vector_weight: float = 0.7, 
                     text_weight: float = 0.3, k: int = 10, 
                     vector_field: str = "vector", 
                     text_field: str = "text") -> List[Dict]:
        """混合搜索(向量+文本)"""
        pipeline = [
            {
                "$search": {
                    "index": "hybrid_index",  # 需要预先创建联合索引
                    "compound": {
                        "should": [
                            {
                                "knnBeta": {
                                    "vector": query_vector,
                                    "path": vector_field,
                                    "k": k * 2  # 扩大候选集
                                }
                            },
                            {
                                "text": {
                                    "query": text_query,
                                    "path": text_field
                                }
                            }
                        ],
                        "score": {
                            "weights": {
                                "knnBeta": vector_weight,
                                "text": text_weight
                            }
                        }
                    }
                }
            },
            {
                "$limit": k
            },
            {
                "$project": {
                    "score": {"$meta": "searchScore"},
                    "_id": 1,
                    vector_field: 1,
                    text_field: 1,
                    "metadata": "$$ROOT"
                }
            }
        ]
        
        return self.aggregate(collection_name, pipeline)
    
    def create_hybrid_index(self, collection_name: str, 
                           vector_field: str = "vector", 
                           text_field: str = "text"):
        """创建混合索引(向量+文本)"""
        index_config = {
            "name": "hybrid_index",
            "definition": {
                "mappings": {
                    "dynamic": True,
                    "fields": {
                        vector_field: {
                            "dimensions": self.vector_dimension,
                            "similarity": "cosine",
                            "type": "knnVector"
                        },
                        text_field: {
                            "type": "string"
                        }
                    }
                }
            }
        }
        
        self.db.command({
            "createSearchIndexes": collection_name,
            "indexes": [index_config]
        })
    
    def batch_vector_search(self, collection_name: str, query_vectors: List[List[float]], 
                           k: int = 10, vector_field: str = "vector") -> List[List[Dict]]:
        """批量向量搜索"""
        results = []
        for query_vector in query_vectors:
            result = self.vector_search(collection_name, query_vector, k, vector_field)
            results.append(result)
        return results
    
    def upsert_vector_document(self, collection_name: str, query: Dict, 
                              vector: List[float], metadata: Dict = None, 
                              vector_field: str = "vector") -> int:
        """更新或插入向量文档"""
        if metadata is None:
            metadata = {}
            
        update_data = {
            "$set": {
                vector_field: vector,
                **metadata
            }
        }
        
        result = self.db[collection_name].update_one(query, update_data, upsert=True)
        return result.modified_count or result.upserted_id is not None
    
    def delete_vector_documents(self, collection_name: str, query: Dict) -> int:
        """删除向量文档"""
        return self.delete_many(collection_name, query)


class VectorUtils:
    """向量工具类"""
    
    @staticmethod
    def cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        a = np.array(vector_a)
        b = np.array(vector_b)
        
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0
        
        return np.dot(a, b) / (norm_a * norm_b)
    
    @staticmethod
    def euclidean_distance(vector_a: List[float], vector_b: List[float]) -> float:
        """计算两个向量的欧氏距离"""
        a = np.array(vector_a)
        b = np.array(vector_b)
        
        return np.linalg.norm(a - b)
    
    @staticmethod
    def dot_product(vector_a: List[float], vector_b: List[float]) -> float:
        """计算两个向量的点积"""
        return np.dot(np.array(vector_a), np.array(vector_b))
    
    @staticmethod
    def normalize_vector(vector: List[float]) -> List[float]:
        """向量归一化"""
        v = np.array(vector)
        norm = np.linalg.norm(v)
        
        if norm == 0:
            return vector
        
        return (v / norm).tolist()
    
    @staticmethod
    def average_vectors(vectors: List[List[float]]) -> List[float]:
        """计算多个向量的平均向量"""
        if not vectors:
            return []
        
        avg_vector = np.mean(np.array(vectors), axis=0)
        return avg_vector.tolist()



# 示例用法
if __name__ == "__main__":
    # # 基础MongoDB操作示例
    # mongo = MongoDBBase("mongodb://localhost:27017/", "mymongo")
    # mongo.insert_one("test_collection", {"name": "测试", "value": 123})
    
    # # 向量数据库示例
    # vector_db = VectorDB("mongodb://localhost:27017/", "vector_db", 768)
    # vector_db.create_vector_collection("embeddings")
    
    # # 插入向量
    # test_vector = [0.1] * 768
    # vector_db.insert_vector_document("embeddings", test_vector, {"text": "示例文本"})
    
    # # 向量搜索
    # similar_docs = vector_db.vector_search("embeddings", test_vector, k=5)
    
    # # 使用向量工具
    # vec_a = [1.0, 2.0, 3.0]
    # vec_b = [4.0, 5.0, 6.0]
    # similarity = VectorUtils.cosine_similarity(vec_a, vec_b)
    pass