"""
測試解析器實例是否能夠正常工作
"""

import asyncio


async def test_parser_instances():
    """測試解析器實例是否能夠正常工作"""
    try:
        print("正在導入解析器實例...")
        from src.agents.parsers.instances import parsers

        print("成功導入解析器延遲加載器")

        # 測試 budget_parser_agent
        print("測試 budget_parser_agent...")
        result = await parsers.budget_parser_agent.process("我想找2000元的飯店")
        print(f"budget_parser_agent 結果: {result}")

        # 測試 date_parser_agent
        print("測試 date_parser_agent...")
        result = await parsers.date_parser_agent.process("我想找明天的飯店")
        print(f"date_parser_agent 結果: {result}")

        print("所有測試通過!")
        return True
    except Exception as e:
        print(f"測試失敗: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_parser_instances())
