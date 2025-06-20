import sys
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# 添加项目根目录到系统路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from connector.base_connector import BaseConnector
from .gewechat_channel import GeWeChatChannel
from .gewechat_message import GeWeChatMessage
from conf.config import CONF
from .common.log import logger
from .context import Context, ContextType
from .reply import Reply, ReplyType

class GeWeChatConnector(BaseConnector):
    """GeWeChat connector implementation"""
    
    def __init__(self):
        gewechat_config = CONF.get("dev", {}).get("gewechat", {})
        super().__init__(loop_time=gewechat_config.get("loop_time", 1))
        
        # Initialize MongoDB connection using existing configuration
        mongodb_config = CONF.get("dev", {}).get("mongodb", {})
        self.mongodb_config = {
            "ip": mongodb_config.get("mongodb_ip"),
            "port": mongodb_config.get("mongodb_port"),
            "name": mongodb_config.get("mongodb_name")
        }
        
        # Initialize WeChat channel
        self.channel = GeWeChatChannel()
        self.bot_wxid = gewechat_config.get("bot_wxid")

    async def startup(self):
        """Initialize the connector"""
        try:
            # Start WeChat channel
            success = await self.channel.startup()
            if not success:
                logger.error("Failed to start GeWeChat channel")
                return False

            logger.info("GeWeChat connector started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting GeWeChat connector: {str(e)}", exc_info=True)
            return False

    async def shutdown(self):
        """Cleanup resources"""
        try:
            await self.channel.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down GeWeChat connector: {str(e)}", exc_info=True)

    async def input_handler(self):
        """Handle incoming messages from WeChat"""
        try:
            msg = await self.channel.get_message()
            if not msg:
                return

            gewechat_msg = GeWeChatMessage(msg, self.channel.client)
            
            # Skip messages that shouldn't be processed
            if not self._should_process_message(gewechat_msg):
                return
                
            # Convert to standard input message format
            input_msg = self._convert_to_input_message(gewechat_msg)
            
            # Use project's MongoDB client to save message
            await self._save_input_message(input_msg)
            
        except Exception as e:
            logger.error(f"Error in input handler: {str(e)}", exc_info=True)

    async def output_handler(self):
        """Handle outgoing messages to WeChat"""
        try:
            # Get pending messages from MongoDB
            pending_msgs = await self._get_pending_messages()

            for msg in pending_msgs:
                result = await self.channel.send_message(msg)
                
                # Update message status
                await self._update_message_status(msg["_id"], result)
                
        except Exception as e:
            logger.error(f"Error in output handler: {str(e)}", exc_info=True)

    def _should_process_message(self, msg: GeWeChatMessage) -> bool:
        """Check if message should be processed"""
        # Skip messages from self
        if msg.from_user_id == self.bot_wxid:
            return False
            
        # Skip non-user messages
        if msg.ctype == ContextType.NON_USER_MSG:
            return False
            
        # Skip status sync messages
        if msg.ctype == ContextType.STATUS_SYNC:
            return False
            
        return True

    def _convert_to_input_message(self, msg: GeWeChatMessage) -> Dict[str, Any]:
        """Convert GeWeChat message to standard format"""
        return {
            "platform": "wechat",
            "message_id": str(msg.msg_id),
            "timestamp": datetime.utcnow(),
            "from_user": msg.from_user_id,
            "to_user": msg.to_user_id,
            "chat_type": "group" if msg.is_group else "private",
            "message_type": msg.ctype.name,
            "content": msg.content,
            "raw_message": msg.msg,
            "metadata": {
                "chatroom_name": msg.chatroom_name if msg.is_group else None,
                "actual_user_id": msg.actual_user_id if msg.is_group else None
            },
            "status": "pending"
        }

    async def _save_input_message(self, msg: Dict[str, Any]):
        """Save input message to MongoDB"""
        # Use project's MongoDB client
        collection = self._get_mongodb_collection("input_messages")
        await collection.insert_one(msg)
        logger.info(f"Saved input message: {msg['message_id']}")

    async def _get_pending_messages(self):
        """Get pending messages from MongoDB"""
        collection = self._get_mongodb_collection("output_messages")
        return await collection.find({
            "platform": "wechat",
            "status": "pending"
        }).to_list(length=100)

    async def _update_message_status(self, msg_id: str, success: bool):
        """Update message status in MongoDB"""
        collection = self._get_mongodb_collection("output_messages")
        await collection.update_one(
            {"_id": msg_id},
            {
                "$set": {
                    "status": "sent" if success else "failed",
                    "updated_at": datetime.utcnow()
                }
            }
        )

    def _get_mongodb_collection(self, collection_name: str):
        """获取MongoDB集合"""
        from common.mongo_client import MongoClient
        client = MongoClient()
        db = client.get_database()
        return db[collection_name]

    async def _process_pending_messages(self):
        """处理待发送的消息"""
        try:
            pending_messages = await self._get_pending_messages()
            for message in pending_messages:
                try:
                    # 根据消息类型处理
                    msg_type = message.get("message_type", "text")
                    content = message.get("content", "")
                    to_user = message.get("to_user", "")
                    
                    success = False
                    if msg_type == "text":
                        # 发送文本消息
                        result = self.client.post_text(self.app_id, to_user, content, "")
                        success = result.get("ret") == 200
                    elif msg_type == "image":
                        # 发送图片消息
                        result = self.client.post_image(self.app_id, to_user, content)
                        success = result.get("ret") == 200
                    elif msg_type == "voice":
                        # 发送语音消息
                        result = self.client.post_voice(self.app_id, to_user, content)
                        success = result.get("ret") == 200
                    
                    # 更新消息状态
                    await self._update_message_status(message["_id"], success)
                    logger.info(f"[gewechat] 处理消息 {message['_id']}: {'成功' if success else '失败'}")
                    
                except Exception as e:
                    logger.error(f"[gewechat] 处理消息 {message.get('_id', 'unknown')} 出错: {str(e)}", exc_info=True)
                    await self._update_message_status(message["_id"], False)
        except Exception as e:
            logger.error(f"[gewechat] 处理待发送消息时出错: {str(e)}", exc_info=True)

    async def run(self):
        """运行连接器"""
        logger.info("[gewechat] 启动 GeWeChat 连接器")
        
        try:
            # 启动 channel
            if not await self.startup():
                logger.error("[gewechat] 启动失败")
                return
            
            # 主循环
            while True:
                try:
                    # 处理输入消息
                    await self.input_handler()
                    
                    # 处理输出消息
                    await self.output_handler()
                    
                    # 等待一段时间
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"[gewechat] 连接器运行出错: {str(e)}", exc_info=True)
                    await asyncio.sleep(10)  # 出错后等待较长时间再重试
        except Exception as e:
            logger.error(f"[gewechat] 连接器运行出错: {str(e)}", exc_info=True)
        finally:
            await self.shutdown()

if __name__ == "__main__":
    from .common.log import logger
    from conf.config import CONF, save_config
    from .lib.client import GewechatClient
    
    # 创建事件循环并运行连接器
    loop = asyncio.get_event_loop()
    connector = GeWeChatConnector()
    try:
        loop.run_until_complete(connector.run())
    except KeyboardInterrupt:
        logger.info("[gewechat] 连接器已停止")
    finally:
        loop.close()
