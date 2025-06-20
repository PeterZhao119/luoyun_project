import os
import time
import json
import threading
import web
from urllib.parse import urlparse
import queue
import uuid

from .context import Context, ContextType
from .reply import Reply, ReplyType
from .common.log import logger
from .common.singleton import singleton
from .common.tmp_dir import TmpDir
from .common.utils import convert_webp_to_png
from .lib.client import GewechatClient
from .common.audio_convert import mp3_to_silk
from .gewechat_message import GeWeChatMessage
from conf.config import CONF, save_config

MAX_UTF8_LEN = 2048

@singleton
class GeWeChatChannel:
    def __init__(self):
        # 消息队列，用于存储待处理的消息
        self.msg_queue = queue.Queue()
        
        # 初始化配置
        gewechat_config = CONF.get("dev", {}).get("gewechat", {})
        self.base_url = gewechat_config.get("gewechat_base_url")
        if not self.base_url:
            logger.error("[gewechat] base_url is not set")
            return
            
        self.token = gewechat_config.get("gewechat_token")
        self.client = GewechatClient(self.base_url, self.token)
        
        # 初始化其他配置
        self.app_id = gewechat_config.get("gewechat_app_id")
        self.download_url = gewechat_config.get("gewechat_download_url")
        
        # 如果token为空，尝试获取token
        if not self.token:
            self._init_token()

        logger.info(f"[gewechat] init: base_url: {self.base_url}, token: {self.token}, app_id: {self.app_id}, download_url: {self.download_url}")

    def _init_token(self):
        """初始化token"""
        logger.warning("[gewechat] token is not set, trying to get token")
        token_resp = self.client.get_token()
        if token_resp.get("ret") != 200:
            logger.error(f"[gewechat] get token failed: {token_resp}")
            return
            
        self.token = token_resp.get("data")
        print(f"[gewechat] token: {self.token}")
        gewechat_config = CONF.get("dev", {}).get("gewechat", {})
        gewechat_config["gewechat_token"] = self.token
        save_config()
        logger.info(f"[gewechat] new token saved: {self.token}")
        self.client = GewechatClient(self.base_url, self.token)

    async def startup(self):
        """启动channel"""
        try:
            # 登录并获取app_id
            app_id, error_msg = self.client.login(self.app_id)
            if error_msg:
                logger.error(f"[gewechat] login failed: {error_msg}")
                return False

            # 保存新的app_id
            if not self.app_id or self.app_id != app_id:
                self.app_id = app_id
                print(f"[gewechat] app_id: {app_id}")
                gewechat_config = CONF.get("dev", {}).get("gewechat", {})
                gewechat_config["gewechat_app_id"] = app_id
                save_config()
                logger.info(f"[gewechat] new app_id saved: {app_id}")

            # 启动回调服务器
            callback_url = CONF.get("gewechat_callback_url")
            if not callback_url:
                logger.error("[gewechat] callback_url is not set")
                return False
            
            # 注意：由于我们只是测试，先不启动回调服务器
            # self._start_callback_server(callback_url)
            return True
            
        except Exception as e:
            logger.error(f"[gewechat] Error starting channel: {str(e)}", exc_info=True)
            return False

    async def shutdown(self):
        """关闭channel"""
        logger.info("[gewechat] shutting down")
        return True

    async def get_message(self):
        """获取消息"""
        try:
            return self.produce()
        except Exception as e:
            logger.error(f"[gewechat] Error getting message: {str(e)}", exc_info=True)
            return None

    async def send_message(self, msg):
        """发送消息"""
        try:
            # 这里实现发送消息的逻辑
            logger.info(f"[gewechat] sending message: {msg}")
            return True
        except Exception as e:
            logger.error(f"[gewechat] Error sending message: {str(e)}", exc_info=True)
            return False

    def _start_callback_server(self, callback_url):
        """启动回调服务器"""
        def set_callback():
            time.sleep(3)  # 等待服务器启动
            try:
                resp = self.client.set_callback(self.token, callback_url)
                if resp.get("ret") != 200:
                    logger.error(f"[gewechat] set callback failed: {resp}")
            except Exception as e:
                logger.error(f"[gewechat] Error setting callback: {str(e)}")
                
        # 启动回调设置线程
        callback_thread = threading.Thread(target=set_callback, daemon=True)
        callback_thread.start()
        
        # 解析回调URL
        parsed_url = urlparse(callback_url)
        path = parsed_url.path
        port = parsed_url.port or 80
        
        # 启动web服务器
        logger.info(f"[gewechat] start callback server: {callback_url}, using port {port}")
        urls = (path, "connector.gewechat.gewechat_channel.Query")
        app = web.application(urls, globals(), autoreload=False)
        web.httpserver.runsimple(app.wsgifunc(), ("0.0.0.0", port))

    def produce(self):
        """获取一条待处理的消息"""
        try:
            return self.msg_queue.get_nowait()
        except queue.Empty:
            return None

    def send(self, reply: Reply, context: Context):
        """发送消息"""
        try:
            receiver = context["receiver"]
            gewechat_message = context.get("msg")
            
            if reply.type in [ReplyType.TEXT, ReplyType.ERROR, ReplyType.INFO]:
                # 发送文本消息
                reply_text = reply.content
                ats = ""
                if gewechat_message and gewechat_message.is_group:
                    ats = gewechat_message.actual_user_id
                self.client.post_text(self.app_id, receiver, reply_text, ats)
                logger.info(f"[gewechat] Sent text to {receiver}: {reply_text}")
                
            elif reply.type == ReplyType.VOICE:
                # 发送语音消息
                self._send_voice(reply, receiver)
                    
            elif reply.type in [ReplyType.IMAGE, ReplyType.IMAGE_URL]:
                # 发送图片消息
                self._send_image(reply, receiver)
                
        except Exception as e:
            logger.error(f"[gewechat] Error sending message: {str(e)}", exc_info=True)

    def _send_voice(self, reply: Reply, receiver: str):
        """发送语音消息"""
        try:
            content = reply.content
            if not content.endswith('.mp3'):
                logger.error(f"[gewechat] voice file is not mp3, path: {content}")
                return
                
            silk_path = content + '.silk'
            duration = mp3_to_silk(content, silk_path)
            callback_url = CONF.get("gewechat_callback_url")
            silk_url = callback_url + "?file=" + silk_path
            self.client.post_voice(self.app_id, receiver, silk_url, duration)
            logger.info(f"[gewechat] Sent voice to {receiver}: {silk_url}")
        except Exception as e:
            logger.error(f"[gewechat] Error sending voice: {str(e)}", exc_info=True)

    def _send_image(self, reply: Reply, receiver: str):
        """发送图片消息"""
        try:
            image_storage = reply.content
            
            # 如果是图片URL，先下载
            if reply.type == ReplyType.IMAGE_URL:
                import requests
                import io
                
                img_url = reply.content
                logger.debug(f"[gewechat] Download image: {img_url}")
                pic_res = requests.get(img_url, stream=True)
                image_storage = io.BytesIO()
                for block in pic_res.iter_content(1024):
                    image_storage.write(block)
                image_storage.seek(0)
                
                # 处理webp格式
                if ".webp" in img_url:
                    image_storage = convert_webp_to_png(image_storage)

            # 保存图片到临时目录
            image_storage.seek(0)
            header = image_storage.read(6)
            image_storage.seek(0)
            img_data = image_storage.read()
            
            # 确定文件扩展名
            extension = ".gif" if header.startswith((b'GIF87a', b'GIF89a')) else ".png"
            img_file_name = f"img_{str(uuid.uuid4())}{extension}"
            img_file_path = os.path.join(TmpDir().path(), img_file_name)
            
            with open(img_file_path, "wb") as f:
                f.write(img_data)
            
            # 构建回调URL并发送
            callback_url = CONF.get("gewechat_callback_url")
            img_url = callback_url + "?file=" + img_file_path
            
            if extension == ".gif":
                result = self.client.post_file(self.app_id, receiver, file_url=img_url, file_name=img_file_name)
            else:
                result = self.client.post_image(self.app_id, receiver, img_url)
                
            logger.info(f"[gewechat] Sent image to {receiver}: {img_url}")
            
            # 处理发送结果
            if result.get('ret') == 200:
                newMsgId = result['data'].get('newMsgId')
                if newMsgId:
                    new_img_file_path = os.path.join(TmpDir().path(), str(newMsgId) + extension)
                    os.rename(img_file_path, new_img_file_path)
                    logger.info(f"[gewechat] Renamed image to {new_img_file_path}")
                    
        except Exception as e:
            logger.error(f"[gewechat] Error sending image: {str(e)}", exc_info=True)

class Query:
    def GET(self):
        """处理GET请求，主要用于文件服务"""
        params = web.input(file="")
        file_path = params.file
        if file_path:
            # 使用os.path.abspath清理路径
            clean_path = os.path.abspath(file_path)
            # 获取tmp目录的绝对路径
            tmp_dir = os.path.abspath(TmpDir().path())
            # 检查文件路径是否在tmp目录下
            if not clean_path.startswith(tmp_dir):
                logger.error(f"[gewechat] Forbidden access to file outside tmp directory: file_path={file_path}")
                raise web.forbidden()

            if os.path.exists(clean_path):
                # 设置正确的Content-Type
                ext = os.path.splitext(clean_path)[1].lower()
                content_type = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.mp3': 'audio/mpeg',
                    '.silk': 'audio/silk',
                }.get(ext, 'application/octet-stream')
                
                web.header('Content-Type', content_type)
                with open(clean_path, 'rb') as f:
                    return f.read()
            else:
                logger.error(f"[gewechat] File not found: {clean_path}")
                raise web.notfound()
        return "gewechat callback server is running"

    def POST(self):
        """处理POST请求，接收微信消息"""
        try:
            # 获取POST数据
            data = web.data()
            if not data:
                return {"ret": 500, "msg": "empty data"}
            
            # 解析JSON数据
            try:
                msg_data = json.loads(data)
            except json.JSONDecodeError:
                logger.error("[gewechat] Invalid JSON data received")
                return {"ret": 500, "msg": "invalid json"}

            # 获取GeWeChatChannel实例
            channel = GeWeChatChannel()
            
            # 处理不同类型的消息
            msg_type = msg_data.get("TypeName")
            if msg_type == "NewMsg":
                # 创建GeWeChatMessage对象
                message = GeWeChatMessage(msg_data)
                
                # 将消息放入队列
                if message.is_valid():
                    channel.msg_queue.put(message)
                    logger.debug(f"[gewechat] Received new message: {message}")
                else:
                    logger.warning(f"[gewechat] Invalid message received: {msg_data}")
                    
            elif msg_type == "ModContacts":
                # 处理联系人变更消息
                logger.debug(f"[gewechat] Received contact update: {msg_data}")
                
            elif msg_type == "TokenExpired":
                # 处理token过期
                logger.warning("[gewechat] Token expired, reinitializing...")
                channel._init_token()
                
            else:
                logger.debug(f"[gewechat] Received unknown message type: {msg_type}")

            return {"ret": 200, "msg": "ok"}
            
        except Exception as e:
            logger.error(f"[gewechat] Error processing message: {str(e)}", exc_info=True)
            return {"ret": 500, "msg": str(e)}

