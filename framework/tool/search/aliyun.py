import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def aliyun_search(messages, model="qwq-plus", stream=True, extra_body=None):
    if extra_body is None:
        extra_body = {
            "enable_search": True,
            "search_options": {
                "forced_search": True,
                "enable_source": True,
                # "enable_citation": True,
                "search_strategy": "pro",
            }
        }

    completion = client.chat.completions.create(
        # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        model=model,
        messages=messages,
        # messages=[
        #     {"role": "system", "content": "你是一个优秀的金融分析师，可以搜索最新的金融消息并且专业地回答用户问题："},
        #     {"role": "user", "content": "今天是2025年6月3日，请帮搜索泡泡玛特这家公司的最新信息，并回答以下内容：1. 公司基本信息（名称，股票代码，上市地点等等）2. 公司基本业务模式：包括公司所属行业，主营业务，主要竞争对手 3. 公司业务模型，包括营收拆分和成本拆分 4. 公司当前的key value driver 5. 基于这些key value driver，会有哪些潜在的catalyst需要关注 6. 公司面临哪些风险。\n\n请尽量以最新的消息为准；如果有多个消息相互矛盾，请尽量相互比较，采纳更加置信的消息，或者更新的消息。"},
        # ],
        stream=stream,
        extra_body=extra_body
        # Qwen3模型通过enable_thinking参数控制思考过程（开源版默认True，商业版默认False）
        # 使用Qwen3开源版模型时，若未启用流式输出，请将下行取消注释，否则会报错
        # extra_body={"enable_thinking": False},
    )

    # print(completion.choices[0].message.content)
    result = ""
    for chunk in completion:
        content = chunk.choices[0].delta.content
        if content is not None:
            result = result + content
        
    return result

# messages=[
#     {"role": "system", "content": "你是一个优秀的金融分析师，可以搜索最新的金融消息并且专业地回答用户问题："},
#     {"role": "user", "content": "今天是2025年6月3日，请帮搜索泡泡玛特这家公司的最新信息，并回答以下内容：1. 公司基本信息（名称，股票代码，上市地点等等）2. 公司基本业务模式：包括公司所属行业，主营业务，主要竞争对手 3. 公司业务模型，包括营收拆分和成本拆分 4. 公司当前的key value driver 5. 基于这些key value driver，会有哪些潜在的catalyst需要关注 6. 公司面临哪些风险。\n\n请尽量以最新的消息为准；如果有多个消息相互矛盾，请尽量相互比较，采纳更加置信的消息，或者更新的消息。"},
# ]
# results = aliyun_search(messages, model="qwq-plus")
# for result in results:
#     print(result, end="")