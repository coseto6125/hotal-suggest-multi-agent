import re


def test_budget_parser():
    query = "最多15000元 2大1小 03/20至03-21 信義區"

    # 模擬 BudgetParserAgent 的解析流程
    currency_units = r"(?:元|塊|NT\$|台幣|TWD|NTD|新台幣)?"
    time_units = r"(?:/晚|每晚|一晚)?"
    num_pattern = r"(\d+(?:,\d+)?(?:\.\d+)?)"

    patterns = {
        "range": re.compile(rf"{num_pattern}\s*(?:-|~|到)\s*{num_pattern}\s*{currency_units}{time_units}"),
        "limit": re.compile(rf"(?:最低|至少|起碼|最高|最多|不超過)\s*{num_pattern}\s*{currency_units}{time_units}"),
        "approx": re.compile(rf"{num_pattern}\s*{currency_units}{time_units}\s*(?:左右|上下|附近|大約)"),
        "any": re.compile(r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:萬|k|K|千|元|塊|NTD|TWD|台幣|新台幣)?"),
    }

    def parse_amount(text, query):
        print(f"解析金額: {text}")
        amount = float(text.replace(",", ""))
        if "萬" in query:
            amount *= 10000
        elif "k" in query.lower() or "千" in query:
            amount *= 1000
        amount = int(amount)
        # 測試最小有效金額判斷（通常是2000）
        MIN_VALID_AMOUNT = 2000
        return amount if amount >= MIN_VALID_AMOUNT else None

    budget = {}

    # 測試範圍模式
    print("\n測試範圍模式:")
    match = patterns["range"].search(query)
    if match:
        print(f"匹配到範圍模式: {match.group()}")
        min_amount = parse_amount(match.group(1), query)
        max_amount = parse_amount(match.group(2), query)
        if min_amount and max_amount:
            budget = {"lowest_price": min_amount, "highest_price": max_amount}
            print(f"預算結果: {budget}")
    else:
        print("未匹配到範圍模式")

    # 測試極限模式（最低/最高）
    print("\n測試極限模式:")
    match = patterns["limit"].search(query)
    if match:
        print(f"匹配到極限模式: {match.group()}")
        print(f"數字部分: {match.group(1)}")
        amount = parse_amount(match.group(1), query)
        if amount:
            print(f"有效金額: {amount}")
            if any(kw in match.group(0) for kw in ["最低", "至少", "起碼"]):
                budget = {"lowest_price": amount, "highest_price": amount * 2}
                print(f"最低預算結果: {budget}")
            elif any(kw in match.group(0) for kw in ["最高", "最多", "不超過"]):
                budget = {"lowest_price": 0, "highest_price": amount}
                print(f"最高預算結果: {budget}")
            print(f"最終預算結果: {budget}")
        else:
            print(f"金額無效: {match.group(1)}")
    else:
        print("未匹配到極限模式")

    # 測試大約模式
    print("\n測試大約模式:")
    match = patterns["approx"].search(query)
    if match:
        print(f"匹配到大約模式: {match.group()}")
        amount = parse_amount(match.group(1), query)
        if amount:
            buffer = int(amount * 0.2)
            budget = {"lowest_price": amount - buffer, "highest_price": amount + buffer}
            print(f"預算結果: {budget}")
    else:
        print("未匹配到大約模式")

    # 測試後備方案
    print("\n測試後備方案:")
    match = patterns["any"].search(query)
    if match:
        print(f"匹配到後備方案: {match.group()}")
        amount = parse_amount(match.group(1), query)
        if amount:
            buffer = int(amount * 0.2)
            if any(kw in query for kw in ["最多", "不超過", "最高"]):
                budget = {"lowest_price": 0, "highest_price": amount}
                print(f"最高預算結果: {budget}")
            else:
                budget = {"lowest_price": amount - buffer, "highest_price": amount + buffer}
                print(f"近似預算結果: {budget}")
    else:
        print("未匹配到後備方案")

    print(f"\n最終預算結果: {budget}")


if __name__ == "__main__":
    test_budget_parser()
