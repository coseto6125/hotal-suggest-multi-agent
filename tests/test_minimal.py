"""
測試 BaseAgent 類的最小腳本
"""

try:
    print("正在嘗試導入 BaseAgent 類...")
    from src.agents.base.base_agent import BaseAgent

    print("成功導入 BaseAgent 類")

    # 創建一個簡單的 BaseAgent 子類
    class SimpleAgent(BaseAgent):
        async def _process(self, inputs):
            return {"result": "success"}

    print("正在嘗試實例化 SimpleAgent...")
    agent = SimpleAgent("SimpleAgent")

    print(f"agent 類型: {type(agent)}")
    print("SimpleAgent 實例化成功!")
except Exception as e:
    print(f"發生錯誤: {e}")
