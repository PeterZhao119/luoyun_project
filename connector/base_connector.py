# -*- coding: utf-8 -*-
import os
import time
import asyncio

import traceback
import logging
from logging import getLogger
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

import sys
sys.path.append(".")

class BaseConnector():
    def __init__(self, loop_time=1):
        self.loop_time = loop_time
    
    async def input_handler(self):
        logger.info("base_input")
        pass

    async def output_handler(self):
        logger.info("base_output")
        pass

    async def input_runner(self):
        while True:
            await asyncio.sleep(self.loop_time)
            await self.input_handler()

    async def output_runner(self):
        while True:
            await asyncio.sleep(self.loop_time)
            await self.output_handler()
    
    async def runner(self):
        await asyncio.gather(
            self.input_runner(),
            self.output_runner()
        )

# 启动脚本
if __name__ == "__main__":
    connector = BaseConnector()
    asyncio.run(connector.runner())