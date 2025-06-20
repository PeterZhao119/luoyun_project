import sys
sys.path.append(".")
import asyncio
from qiaoyun.runner.qiaoyun_handler import main_handler
from qiaoyun.runner.qiaoyun_background_handler import background_handler

async def run_main_agent():
    while True:
        await asyncio.sleep(1)
        await main_handler()

async def run_background_agent():
    while True:
        await asyncio.sleep(1)
        await background_handler()

async def main():
    await asyncio.gather(
        run_main_agent(),
        run_background_agent()
    )

asyncio.run(main())