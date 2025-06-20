import json
import os


def init_conf():
    conf = {}
    with open("conf/config.json", mode="r") as f:
        conf = json.load(f)
    env = os.getenv("env", "dev")
    # 定制化配置覆盖原配置
    server_conf = conf.get(env) or {}
    conf.update(server_conf)
    return conf

def save_config():
    """保存配置到文件"""
    with open("conf/config.json", mode="w", encoding="utf-8") as f:
        json.dump(CONF, f, ensure_ascii=False, indent=4)

CONF = init_conf()
