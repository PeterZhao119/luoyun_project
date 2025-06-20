from flask import Flask, request, jsonify
import requests
import logging
import sys
sys.path.append(".")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

from dao.mongo import MongoDBBase
from dao.user_dao import UserDAO

from connector.ecloud.ecloud_api import Ecloud_API
from connector.ecloud.ecloud_adapter import ecloud_message_to_std, std_to_ecloud_message

mongo = MongoDBBase()
user_dao = UserDAO()

# Whitelist dictionary - wcId as key, forwarding URL as value
# You can modify this dictionary as needed
whitelist = {
    "wxid_phyyedw9xap22": "http://example.com/forward1",
    "wxid_1dfgh4fs8vz22": "http://example.com/forward2",
    # Add more entries as needed
}

user_whitelist = []
# user_whitelist = ["LeanInWind", "z4656207", "wxid_vex849hfamd822", "samueli", "DoonsSong", "annie--y"]

supported_message_types = [
    "60001", #私聊文本
    "60014", #私聊引用
    "60004", #私聊语音
    "60002", #私聊图片
    ]

@app.route('/message', methods=['POST'])
def handle_message():
    """
    Handle incoming message requests and forward them based on wcId
    """
    if not request.is_json:
        logger.warning("Request is not JSON")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400
    
    # Get the JSON data
    data = request.get_json()
    logger.info(data)
    
    # Extract wcId from the request
    wcId = data.get('wcId')
    
    if not wcId:
        logger.warning("No wcId in request")
        return jsonify({"status": "error", "message": "No wcId provided"}), 400
    
    # Check if wcId is in whitelist
    if data["data"]["fromUser"] in whitelist:
        forward_url = whitelist[wcId]
        
        try:
            # Forward the request to the corresponding URL
            logger.info(f"Forwarding request for wcId {wcId} to {forward_url}")
            response = requests.post(
                forward_url,
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            # Return the response from the forwarded request
            return jsonify({
                "status": "success",
                "message": f"Request forwarded to {forward_url}",
                "forward_status": response.status_code,
                "forward_response": response.json() if response.headers.get('content-type') == 'application/json' else response.text
            })
            
        except requests.RequestException as e:
            logger.error(f"Error forwarding request: {str(e)}")
            return jsonify({
                "status": "error", 
                "message": f"Error forwarding request: {str(e)}"
            }), 500
    else:
        logger.info(f"message incoming, handling...")

        # 支持的类型
        if data["messageType"] not in supported_message_types:
            logger.info("not supported message type.")
            return jsonify({
                "status": "success", 
                "message": "not supported message type."
            }), 200

        # 白名单
        if len(user_whitelist) != 0:
            if data["data"]["fromUser"] not in user_whitelist:
                logger.info("user not in white list, ignore this message")
                return jsonify({
                    "status": "success", 
                    "message": "user not in white list, ignore this message"
                }), 200

        # 验证character或者user是否存在
        characters = user_dao.find_characters({
            "platforms.wechat.id": data["data"]["toUser"]
        })

        if len(characters) == 0:
            return jsonify({
                "status": "success", 
                "message": "character not exist, skip..."
            }), 200
        
        cid = str(characters[0]["_id"])
        
        users = user_dao.find_users({
            "platforms.wechat.account": data["data"]["fromUser"]
        })

        # 如果用户不存在，则创建一个
        if len(users) == 0:
            logger.info("user not exist, create a new one")
            target_user_alias = characters[0]["name"]
            resp_json = Ecloud_API.getContact(data["data"]["fromUser"], target_user_alias)
            logger.info(resp_json)
            user_wechat_info = resp_json["data"][0]

            uid = user_dao.create_user({
                "is_character": False,  # 是否是角色
                "name": user_wechat_info["userName"],  # 统一注册名
                "platforms": {
                    "wechat": {
                        "id": data["data"]["fromUser"],  # 微信统一id
                        "account": user_wechat_info["userName"],  # 微信号
                        "nickname": user_wechat_info["nickName"], # 微信昵称
                    },
                },
                "status": "normal",  # normal | stopped
                "user_info": {
                },
                "user_wechat_info": user_wechat_info
            })
        else:
            uid = str(users[0]["_id"])

        # 标准化数据
        std = ecloud_message_to_std(data)
        std["from_user"] = uid
        std["to_user"] = cid

        # 插入到数据库
        mid = mongo.insert_one("inputmessages", std)

        return jsonify({
            "status": "success", 
            "message": "message handing..."
        }), 200

if __name__ == '__main__':
    logger.info("Starting Flask forwarding service")
    app.run(host='0.0.0.0', port=8080, debug=True)