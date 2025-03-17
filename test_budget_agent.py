"""
測試 BudgetParserAgent 類的簡單腳本
"""

try:
    print("正在嘗試導入 BudgetParserAgent 類...")
    from src.agents.parsers.budget_parser_agent import BudgetParserAgent

    print("成功導入 BudgetParserAgent 類")
    print("正在嘗試實例化 BudgetParserAgent...")

    budget_parser = BudgetParserAgent()

    print(f"budget_parser 類型: {type(budget_parser)}")
    print("BudgetParserAgent 實例化成功!")
except Exception as e:
    print(f"發生錯誤: {e}")
