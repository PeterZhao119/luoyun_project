import sys
sys.path.append(".")
import os
import json

import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)
import traceback

import dashscope
from http import HTTPStatus
from dao.mongo import MongoDBBase

def embedding_by_aliyun(text, model="text-embedding-v3"):
    resp = dashscope.TextEmbedding.call(
        model=model,
        input=text)
    if resp.status_code == HTTPStatus.OK:
        output = resp.output
        return output["embeddings"][0]["embedding"]
    else:
        return None
    
def upsert_one(key, value, metadata, collection_name="embeddings"):
    mongo = MongoDBBase()
    key_embedding = embedding_by_aliyun(key)
    value_embedding = embedding_by_aliyun(value)
    if "type" not in metadata:
        metadata["type"] = "character_global"

    already = mongo.find_one(collection_name, query={
        "metadata.type": metadata["type"],
        "key": key
    })

    if already is None:
        mid = mongo.insert_vector(
            collection_name=collection_name,
            key=key,
            key_embedding=key_embedding,
            value=value,
            value_embedding=value_embedding,
            metadata=metadata
        )
        return mid
    else:
        mb = mongo.update_vector(
            collection_name=collection_name,
            doc_id=str(already["_id"]),
            key=key,
            key_embedding=key_embedding,
            value=value,
            value_embedding=value_embedding,
            metadata=metadata
        )
        if mb:
            return str(already["_id"])
    
    return None

