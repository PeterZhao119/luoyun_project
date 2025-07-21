# -*- coding: utf-8 -*-
import os
import time

import sys
sys.path.append(".")

import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

from framework.agent.base_agent import AgentStatus, BaseAgent
from conf.config import CONF
from volcenginesdkarkruntime import Ark
from dao.mongo import MongoDBBase
from util.embedding_util import embedding_by_aliyun


class QiaoyunContextRetrieveAgent(BaseAgent):
    def __init__(self, context = None, max_retries = 3, name = None):
        super().__init__(context, max_retries, name)
    
    def _execute(self):
        mongo = MongoDBBase()
        q = self.context["query_rewrite"]
        merged_results = {}
        return_resp = {
            "character_global": "",
            "character_private": "",
            "user": "",
            "character_knowledge": "",
            "character_photo": ""
        }

        # 角色全局人物设定
        if q["CharacterSettingQueryQuestion"] != "空":
            emb_CharacterSettingQueryQuestion = embedding_by_aliyun(q["CharacterSettingQueryQuestion"])
            results = mongo.vector_search(
                "embeddings",
                query_embedding=emb_CharacterSettingQueryQuestion,
                embedding_field="key_embedding",
                metadata_filters={
                    "type": "character_global",
                    "cid": str(self.context["character"]["_id"])
                },
                top_k=8,
            )
            merged_results = self.merge_results_embedding(merged_results, results, 0.3, 1, 0.7)

            results = mongo.vector_search(
                "embeddings",
                query_embedding=emb_CharacterSettingQueryQuestion,
                embedding_field="value_embedding",
                metadata_filters={
                    "type": "character_global",
                    "cid": str(self.context["character"]["_id"])
                },
                top_k=8,
            )
            merged_results = self.merge_results_embedding(merged_results, results, 0.3, 1, 0.3)

            results = []
            for keyword in str(q["CharacterSettingQueryKeywords"]).split(","):
                keyword_results = mongo.find_many("embeddings", query={
                    "key": {"$in": [keyword]},
                    "metadata": {
                        "type": "character_global",
                        "cid": str(self.context["character"]["_id"])
                    },
                },
                limit=5)
                results = results + keyword_results
            merged_results = self.merge_results_text(merged_results, results, 1)

            results = []
            for keyword in str(q["CharacterSettingQueryKeywords"]).split(","):
                keyword_results = mongo.find_many("embeddings", query={
                    "value": {"$in": [keyword]},
                    "metadata": {
                        "type": "character_global",
                        "cid": str(self.context["character"]["_id"])
                    }
                },
                limit=5)
                results = results + keyword_results
            merged_results = self.merge_results_text(merged_results, results, 1)
        
        top_n_results = self.top_n(merged_results, 6)
        # logger.info(top_n_results)
        return_resp["character_global"] = top_n_results

        # 角色个人设定
        merged_results = {}
        if q["CharacterSettingQueryQuestion"] != "空":
            emb_CharacterSettingQueryQuestion = embedding_by_aliyun(q["CharacterSettingQueryQuestion"])
            results = mongo.vector_search(
                "embeddings",
                query_embedding=emb_CharacterSettingQueryQuestion,
                embedding_field="key_embedding",
                metadata_filters={
                    "type": "character_private",
                    "cid": str(self.context["character"]["_id"]),
                    "uid": str(self.context["user"]["_id"])
                },
                top_k=8,
            )
            merged_results = self.merge_results_embedding(merged_results, results, 0.3, 1, 0.7)

            results = mongo.vector_search(
                "embeddings",
                query_embedding=emb_CharacterSettingQueryQuestion,
                embedding_field="value_embedding",
                metadata_filters={
                    "type": "character_private",
                    "cid": str(self.context["character"]["_id"]),
                    "uid": str(self.context["user"]["_id"])
                },
                top_k=8,
            )
            merged_results = self.merge_results_embedding(merged_results, results, 0.3, 1, 0.3)

            results = []
            for keyword in str(q["CharacterSettingQueryKeywords"]).split(","):
                keyword_results = mongo.find_many("embeddings", query={
                    "key": {"$in": [keyword]},
                    "metadata": {
                        "type": "character_private",
                        "cid": str(self.context["character"]["_id"]),
                        "uid": str(self.context["user"]["_id"])
                    },
                },
                limit=5)
                results = results + keyword_results
            merged_results = self.merge_results_text(merged_results, results, 1)

            results = []
            for keyword in str(q["CharacterSettingQueryKeywords"]).split(","):
                keyword_results = mongo.find_many("embeddings", query={
                    "value": {"$in": [keyword]},
                    "metadata": {
                        "type": "character_private",
                        "cid": str(self.context["character"]["_id"]),
                        "uid": str(self.context["user"]["_id"])
                    }
                },
                limit=5)
                results = results + keyword_results
            merged_results = self.merge_results_text(merged_results, results, 1)
        
            top_n_results = self.top_n(merged_results, 6)
            # logger.info(top_n_results)
            return_resp["character_private"] = top_n_results

        # 用户个人设定
        merged_results = {}
        if q["UserProfileQueryQuestion"] != "空":
            emb_CharacterSettingQueryQuestion = embedding_by_aliyun(q["UserProfileQueryQuestion"])
            results = mongo.vector_search(
                "embeddings",
                query_embedding=emb_CharacterSettingQueryQuestion,
                embedding_field="key_embedding",
                metadata_filters={
                    "type": "user",
                    "cid": str(self.context["character"]["_id"]),
                    "uid": str(self.context["user"]["_id"])
                },
                top_k=8,
            )
            merged_results = self.merge_results_embedding(merged_results, results, 0.3, 1, 0.7)

            results = mongo.vector_search(
                "embeddings",
                query_embedding=emb_CharacterSettingQueryQuestion,
                embedding_field="value_embedding",
                metadata_filters={
                    "type": "user",
                    "cid": str(self.context["character"]["_id"]),
                    "uid": str(self.context["user"]["_id"])
                },
                top_k=8,
            )
            merged_results = self.merge_results_embedding(merged_results, results, 0.3, 1, 0.3)

            results = []
            for keyword in str(q["UserProfileQueryKeywords"]).split(","):
                keyword_results = mongo.find_many("embeddings", query={
                    "key": {"$in": [keyword]},
                    "metadata": {
                        "type": "user",
                        "cid": str(self.context["character"]["_id"]),
                        "uid": str(self.context["user"]["_id"])
                    },
                },
                limit=5)
                results = results + keyword_results
            merged_results = self.merge_results_text(merged_results, results, 1)

            results = []
            for keyword in str(q["UserProfileQueryKeywords"]).split(","):
                keyword_results = mongo.find_many("embeddings", query={
                    "value": {"$in": [keyword]},
                    "metadata": {
                        "type": "user",
                        "cid": str(self.context["character"]["_id"]),
                        "uid": str(self.context["user"]["_id"])
                    }
                },
                limit=5)
                results = results + keyword_results
            merged_results = self.merge_results_text(merged_results, results, 1)
        
            top_n_results = self.top_n(merged_results, 6)
            # logger.info(top_n_results)
            return_resp["user"] = top_n_results

        # 角色相册
        merged_results = {}
        if q["CharacterPhotoQueryQuestion"] != "空":
            emb_CharacterSettingQueryQuestion = embedding_by_aliyun(q["CharacterPhotoQueryQuestion"])
            results = mongo.vector_search(
                "embeddings",
                query_embedding=emb_CharacterSettingQueryQuestion,
                embedding_field="key_embedding",
                metadata_filters={
                    "type": "character_photo",
                    "cid": str(self.context["character"]["_id"]),
                },
                top_k=8,
            )
            merged_results = self.merge_results_embedding(merged_results, results, 0.3, 1, 0.7)

            results = mongo.vector_search(
                "embeddings",
                query_embedding=emb_CharacterSettingQueryQuestion,
                embedding_field="value_embedding",
                metadata_filters={
                    "type": "character_photo",
                    "cid": str(self.context["character"]["_id"]),
                },
                top_k=8,
            )
            merged_results = self.merge_results_embedding(merged_results, results, 0.3, 1, 0.3)

            results = []
            for keyword in str(q["CharacterPhotoQueryKeywords"]).split(","):
                keyword_results = mongo.find_many("embeddings", query={
                    "key": {"$in": [keyword]},
                    "metadata": {
                        "type": "character_photo",
                        "cid": str(self.context["character"]["_id"]),
                    },
                },
                limit=8)
                results = results + keyword_results
            merged_results = self.merge_results_text(merged_results, results, 1)

            results = []
            for keyword in str(q["CharacterPhotoQueryKeywords"]).split(","):
                keyword_results = mongo.find_many("embeddings", query={
                    "value": {"$in": [keyword]},
                    "metadata": {
                        "type": "character_photo",
                        "cid": str(self.context["character"]["_id"]),
                    }
                },
                limit=8)
                results = results + keyword_results
            merged_results = self.merge_results_text(merged_results, results, 1)
            
            # 进行频度惩罚
            filtered_merged_results = {}
            for key in merged_results:
                logger.info("merged_result")
                logger.info(merged_results[key])
                already = False
                for already_photo_id in self.context["conversation"]["conversation_info"]["photo_history"]:
                    if str(key) == already_photo_id:
                        already = True
                if already == False:
                    filtered_merged_results[str(key)] = merged_results[key]

            top_n_results = self.top_n(filtered_merged_results, 6, photo_prefix=True)

            # top_n_results = self.top_n(merged_results, 6, photo_prefix=True)
            # logger.info(top_n_results)           

            return_resp["character_photo"] = top_n_results
        
        # 角色知识
        merged_results = {}
        if q["CharacterKnowledgeQueryQuestion"] != "空":
            emb_CharacterSettingQueryQuestion = embedding_by_aliyun(q["CharacterKnowledgeQueryQuestion"])
            results = mongo.vector_search(
                "embeddings",
                query_embedding=emb_CharacterSettingQueryQuestion,
                embedding_field="key_embedding",
                metadata_filters={
                    "type": "character_knowledge",
                    "cid": str(self.context["character"]["_id"]),
                },
                top_k=8,
            )
            merged_results = self.merge_results_embedding(merged_results, results, 0.3, 1, 0.7)

            results = mongo.vector_search(
                "embeddings",
                query_embedding=emb_CharacterSettingQueryQuestion,
                embedding_field="value_embedding",
                metadata_filters={
                    "type": "character_knowledge",
                    "cid": str(self.context["character"]["_id"]),
                },
                top_k=8,
            )
            merged_results = self.merge_results_embedding(merged_results, results, 0.3, 1, 0.3)

            results = []
            for keyword in str(q["CharacterKnowledgeQueryKeywords"]).split(","):
                keyword_results = mongo.find_many("embeddings", query={
                    "key": {"$in": [keyword]},
                    "metadata": {
                        "type": "character_knowledge",
                        "cid": str(self.context["character"]["_id"]),
                    },
                },
                limit=8)
                results = results + keyword_results
            merged_results = self.merge_results_text(merged_results, results, 1)

            results = []
            for keyword in str(q["CharacterKnowledgeQueryKeywords"]).split(","):
                keyword_results = mongo.find_many("embeddings", query={
                    "value": {"$in": [keyword]},
                    "metadata": {
                        "type": "character_knowledge",
                        "cid": str(self.context["character"]["_id"]),
                    }
                },
                limit=8)
                results = results + keyword_results
            merged_results = self.merge_results_text(merged_results, results, 1)

            top_n_results = self.top_n(merged_results, 6)     

            return_resp["character_knowledge"] = top_n_results

        yield return_resp

    def merge_results_embedding(self, merged_results, results, bar_min, bar_max, weight):
        for result in results:
            # 过滤太高的
            if result["similarity"] > bar_max:
                result["similarity"] = bar_max
            if result["similarity"] < bar_min:
                continue

            # 计算weight
            result_weight = weight * (result["similarity"] - bar_min) / (bar_max - bar_min) 

            # 合并
            if str(result["_id"]) not in merged_results:
                merged_results[str(result["_id"])] = {
                    "_id": str(result["_id"]),
                    "key": result["key"],
                    "value": result["value"],
                    "similarity": result["similarity"],
                    "weight": result_weight
                }
            else:
                merged_results[str(result["_id"])]["weight"] = merged_results[str(result["_id"])]["weight"] + result_weight

        return merged_results

    def merge_results_text(self, merged_results, results, total_weight):
        if len(results) == 0:
            return merged_results
        
        # 重整
        reorder_results = []
        for result in results:
            result_weight = total_weight/len(results)
            result["weight"] = result_weight
            reorder_results.append(result)
        
        # 合并
        for reorder_result in reorder_results:
            if str(reorder_result["_id"]) not in merged_results:
                merged_results[str(reorder_result["_id"])] = {
                    "_id": str(result["_id"]),
                    "key": reorder_result["key"],
                    "value": reorder_result["value"],
                    "weight": reorder_result["weight"]
                }
            else:
                merged_results[str(reorder_result["_id"])]["weight"] = merged_results[str(reorder_result["_id"])]["weight"] + reorder_result["weight"]

        return merged_results

    def top_n(self, results, n, photo_prefix=False):
        # 对字典按 weight 值排序
        sorted_items = sorted(
            results.items(), 
            key=lambda x: x[1]['weight'], 
            reverse=True
        )
        
        # 只返回值（不包含键）
        top_n_results = [item[1] for item in sorted_items[:n]]

        # 整理为字符串
        top_n_str_list = []
        for top_n_result in top_n_results:
            top_n_result_line = str(top_n_result["key"] + "：" + top_n_result["value"]).strip()
            if photo_prefix:
                top_n_result_line = "「照片" + str(top_n_result["_id"]) + "」" + top_n_result_line
            top_n_str_list.append(top_n_result_line)
        
        return "\n".join(top_n_str_list)
