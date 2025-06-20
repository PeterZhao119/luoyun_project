import os
import base64
import sys
sys.path.append(".")

# 通过 pip install volcengine-python-sdk[ark] 安装方舟SDK
from volcenginesdkarkruntime import Ark

# 替换 <MODEL> 为模型的Model ID
model="doubao-1-5-thinking-vision-pro-250428"

# 初始化Ark客户端，从环境变量中读取您的API Key
client = Ark(
    api_key=os.getenv('ARK_API_KEY'),
)

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def ark_image2text(prompt, image_url=None, image_path=None, image_format="png"):
    # 如果不使用image_url，使用本地图片
    if image_url is None:
       base64_image = encode_image(image_path)
       image_url = f"data:image/{image_format};base64,{base64_image}"
       
    # 创建一个对话请求
    response = client.chat.completions.create(
        # 指定您部署了视觉理解大模型的推理接入点ID
        model = model,
        messages = [
            {
                # 指定消息的角色为用户
                "role": "user",  
                "content": [   
                    # 图片信息，希望模型理解的图片
                    {"type": "image_url", "image_url": {"url":  image_url},},
                    # 文本消息，希望模型根据图片信息回答的问题
                    {"type": "text", "text": prompt}, 
                ],
            }
        ],
    )

    return response.choices[0].message.content

# 启动脚本
if __name__ == "__main__":
   image_url = "http://wxapii.oos-hazz.ctyunapi.cn/20250605/wxid_7mww7784dgse22/460a6fc1-4c5d-4229-80a3-822aa72035db.png?AWSAccessKeyId=9e882e7187c38b431303&Expires=1749725506&Signature=EB9GA6WDV36Eq3UoRctXQ6vqyz0%3D"

   print(ark_image2text("请详细描述图片中有什么", image_url))
   