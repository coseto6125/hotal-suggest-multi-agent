"""
測試配置文件
"""

import asyncio
from typing import Generator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """創建事件循環"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
