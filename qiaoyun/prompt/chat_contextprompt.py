# -*- coding: utf-8 -*-
CONTEXTPROMPT_时间 = '''### 小说中的当前时间
（24小时制）{conversation[conversation_info][time_str]}'''

CONTEXTPROMPT_新闻 = '''### 今日新闻
{news_str}
'''

CONTEXTPROMPT_人物信息 = '''### {character[platforms][wechat][nickname]}的人物信息
{character[user_info][description]}'''

# "character_global": "",
# "chatacter_private": "",
# "user": "",
# "character_knowledge": "",
# "character_photo": ""

CONTEXTPROMPT_人物资料 = '''### {character[platforms][wechat][nickname]}的人物资料
{context_retrieve[character_global]}
{context_retrieve[chatacter_private]}'''

CONTEXTPROMPT_用户资料 = '''### {user[platforms][wechat][nickname]}的人物资料
{context_retrieve[user]}'''

CONTEXTPROMPT_人物知识和技能 = '''### {character[platforms][wechat][nickname]}的人物知识和技能
{context_retrieve[character_knowledge]}'''

CONTEXTPROMPT_人物手机相册 = '''### {character[platforms][wechat][nickname]}的人物手机相册
{context_retrieve[character_photo]}'''

CONTEXTPROMPT_人物状态 = '''### {character[platforms][wechat][nickname]}的人物状态
所在地点：{character[user_info][status][place]}
行动：{character[user_info][status][action]}
当前状态：{relation[relationship][status]}'''

CONTEXTPROMPT_当前目标 = '''### {character[platforms][wechat][nickname]}的当前目标
长期目标：{relation[character_info][longterm_purpose]}
短期目标：{relation[character_info][shortterm_purpose]}
对{user[platforms][wechat][nickname]}的态度：{relation[character_info][attitude]}'''

CONTEXTPROMPT_当前的人物关系 = '''### {character[platforms][wechat][nickname]}与{user[platforms][wechat][nickname]}当前的人物关系
关系描述：{relation[relationship][description]}
亲密度：{relation[relationship][closeness]}
信任度：{relation[relationship][trustness]}
反感度：{relation[relationship][dislike]}
已知{user[platforms][wechat][nickname]}的真名：{relation[user_info][realname]}
{character[platforms][wechat][nickname]}对{user[platforms][wechat][nickname]}的亲密昵称：{relation[user_info][hobbyname]}
{character[platforms][wechat][nickname]}对{user[platforms][wechat][nickname]}的印象描述：{relation[user_info][description]}
'''

## Relations
# {
#     "_id": "xxx",
#     "uid": "xxx",
#     "cid": "xxx",
#     "user_info": {
#         "realname": "xxx",
#         "hobbyname": "xxx",
#         "description": "xxx",
#     },
#     "character_info": {
#         "longterm_purpose": "xxx",
#         "shortterm_purpose": "xxx",
#         "attitude": "xxx",
#     },
#     "relationship": {
#         "description": "xxx",
#         "closeness": xx,
#         "trustness": xx,
#     },
# }

CONTEXTPROMPT_历史对话 = '''### 历史对话
{conversation[conversation_info][chat_history_str]}'''

CONTEXTPROMPT_最新聊天消息 = '''### {user[platforms][wechat][nickname]}的最新聊天消息
{conversation[conversation_info][input_messages_str]}'''

CONTEXTPROMPT_初步回复 = '''### {character[platforms][wechat][nickname]}的初步回复
{MultiModalResponses}'''

CONTEXTPROMPT_最新聊天消息_双方 = '''### {user[platforms][wechat][nickname]}的最新聊天消息
{conversation[conversation_info][input_messages_str]}

### {character[platforms][wechat][nickname]}的最新回复
{MultiModalResponses}'''

CONTEXTPROMPT_规划行动 = '''### {character[platforms][wechat][nickname]}的规划行动
{conversation[conversation_info][future][action]}'''

