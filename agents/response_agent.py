from typing import Any


class ResponseAgent:
    """回應生成 Agent，負責生成自然語言回應"""

    def __init__(self):
        # TODO: 初始化回應生成 Agent
        ...

    async def generate_initial_response(self, query: str) -> str:
        """生成初步回應"""
        # TODO: 實現初步回應生成邏輯

    async def generate_complete_response(self, results: dict[str, Any]) -> str:
        """生成完整回應"""
        # TODO: 實現完整回應生成邏輯
