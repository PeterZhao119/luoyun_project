# Entity
## users
```
{
    "_id": "xxx", # 内置id
    "is_character": True,  # 是否是角色
    "name": "xxx",  # 统一注册名
    "platforms": {
        "wechat": {
            "id": "xxx",  # 微信统一id
            "account": "xxx",  # 微信号
            "nickname": "xxx", # 微信昵称
        },
        ...
    },
    "status": "xxx",  # normal | stopped
    "user_info": {
        "description": "xxx",
        "status": {
            "place": "xxx",
            "action": "xxx",
            "status": "xxx",
        }
    },
}
```

## conversations
```
{
    "_id": "xxx", # 内置id
    "chatroom_name": None,  # 一般为None，在群聊时展示为频道名
    "talkers": [  # 聊天人群，一般只需要关注第0和第1号位置；如果是群聊消息，则会有多人
        {
            "id": "xxx",
            "nickname": "xxx", # 频道中的昵称，可能与统一昵称不同
        },
        ...
    ],
    "platform": "xxx",  # 所属平台
    "conversation_info": {
        "time_str": "xxx",
        "chat_history": [],
        "chat_history_str": "xxx",
        "input_messages": [],
        "input_messages_str": "",
        "photo_history": [],
        "future": { # 在该对话上规划的未来行动
            "timestamp": "xxx",
            "action": "xxx",
            "proactive_times": 0, # 主动对话次数，用来防止过度骚扰用户
        }
    }
}
```

## relations
```
{
    "_id": "xxx",
    "uid": "xxx",
    "cid": "xxx",
    "user_info": {
        "realname": "xxx",
        "hobbyname": "xxx",
        "description": "xxx",
    },
    "character_info": {
        "longterm_purpose": "xxx",
        "shortterm_purpose": "xxx",
        "attitude": "xxx",
        "status": "xxx", # 繁忙，空闲，睡觉
    },
    "relationship": {
        "description": "xxx",
        "closeness": xx,
        "trustness": xx,
        "dislike": xx,
    },
}
```

# Daily
## dailynews
```
{
    "_id": "xxx",
    "cid": "xxx",
    "news": "xxx",
    "date": "xxx",
}
## dailyscripts
{
    "_id": "xxx",
    "cid": "xxx",
    "date": "xxx",
    "start_timestamp": xxx,
    "end_timestamp": xxx,
    "place": "xxx",
    "action": "xxx",
    "status": "xxx"
}

# Messages
## inputmessages
{
    "_id": xxx,  # 内置id
    "input_timestamp": xxx,  # 输入时的时间戳秒级
    "handled_timestamp": xxx,  # 处理完毕时的时间戳秒级
    "status": "pending",  # 标记处理状态：pending待处理，handled处理完毕，canceled不处理，failed处理失败
    "from_user": "xxx",  # 来源uid
    "platform": "xxx",  # 来源平台
    "chatroom_name": None,  # 如果有值，则来自群聊；否则是私聊
    "to_user": "xxx", # 目标用户；群聊时，值为None
    "message_type": "xxxx",  # 包括：
    "message": "xxx",  # 实际消息，格式另行约定
    "metadata": {
        "file_path": "xxx", # 所包含的文件路径
    }
}
```

## outputmessages
```
{
    "_id": xxx,  # 内置id
    "expect_output_timestamp": xxx,  # 预期输出的时间戳秒级
    "handled_timestamp": xxx,  # 处理完毕时的时间戳秒级
    "status": "pending",  # 标记处理状态：pending待处理，handled处理完毕，canceled不处理，failed处理失败
    "from_user": "xxx",  # 来源uid
    "platform": "xxx",  # 来源平台
    "chatroom_name": None,  # 如果有值，则来自群聊；否则是私聊
    "to_user": "xxx", # 目标用户uid；群聊时，值为None
    "message_type": "xxxx",  # 包括：
    "message": "xxx",  # 实际消息，格式另行约定
    "metadata": {
        "file_path": "xxx", # 所包含的文件路径
    }
}
```
# Embeddgins
## embeddings
```
{
    "key": "xxx",
    "key_embedding": "xxx",
    "value": "xxx",
    "value_embedding": "xxx",
    "metadata": {
        "type": "xxx", 
        # 类型包括：
        # character_global 角色全局设定
        # character_private 角色私有设定
        # user 用户私有设定
        # character_knowledge 角色全局知识（学习，搜索等）
        # character_photo 角色全局手机相册
        "uid": "xxx",
        "cid": "xxx",
        "url": "xxx", # 地址
        "file": "xxxx", # 文件的base64
    }
}
```