"""
旅館推薦生成Agent，負責生成LLM推薦回應，並支持流式輸出
"""

import asyncio
from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent
from src.agents.generators.llm_agent import llm_agent
from src.web.websocket import ws_manager


class HotelRecommendationAgent(BaseAgent):
    """旅館推薦生成Agent - 負責生成LLM推薦回應，並支持流式輸出"""

    def __init__(self):
        """初始化旅館推薦生成Agent"""
        super().__init__("HotelRecommendationAgent")
        self.logger = logger

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """處理生成旅館推薦的方法"""
        self.logger.info("開始生成旅館推薦")

        # 獲取清洗後的旅館和方案資料
        hotel_details = state.get("response", [])
        query = state.get("query", "")
        session_id = state.get("session_id", "")

        # 如果沒有旅館資料，直接返回
        if not hotel_details:
            self.logger.warning("沒有旅館資料可供推薦")
            return state

        # 準備LLM輸入
        llm_input = self._prepare_llm_input(query, hotel_details)

        # 呼叫LLM生成推薦並直接流式輸出到前端
        recommendation = ""
        if session_id:
            recommendation = await self._generate_recommendation_stream(llm_input, session_id)

        # 返回結果
        return {
            **state,
            "recommendation": recommendation,
        }

    def _prepare_llm_input(self, query: str, hotel_details: str) -> str:
        """準備LLM輸入"""
        # 將用戶查詢和旅館資料整合為一個完整的message內容
        message_content = []
        message_content.append(f"用戶需求: {query}\n\n")

        # 添加旅館資料
        if hotel_details["message"]:
            message_content.append("旅館資料:\n")
            message_content.append(f"{hotel_details}\n")
        else:
            message_content.append("旅館資料:")
            message_content.append("無旅館資料\n")

        return "".join(message_content)

    def _format_hotels_for_llm(self, hotels: list[dict[str, Any]]) -> str:
        """將旅館數據格式化為LLM易於理解的文本"""
        if not hotels:
            return "無旅館資料"

        result_lines = []
        for i, hotel in enumerate(hotels[:5]):  # 限制輸入給LLM的資料數量
            hotel_name = hotel.get("name", "未知")
            hotel_address = hotel.get("address", "未知")
            hotel_price = hotel.get("price", "未知")

            result_lines.append(f"{i + 1}. {hotel_name}\n")
            result_lines.append(f"   地址: {hotel_address}\n")
            result_lines.append(f"   價格: {hotel_price} 元/晚\n")

            # 添加地理位置資訊
            county = hotel.get("county", {})
            county_name = county.get("name", "") if county else ""
            district = hotel.get("district", {})
            district_name = district.get("name", "") if district else ""

            if county_name or district_name:
                location = []
                if county_name:
                    location.append(county_name)
                if district_name:
                    location.append(district_name)
                result_lines.append(f"   位置: {', '.join(location)}\n")

            # 添加簡介
            intro = hotel.get("intro", "")
            if intro:
                # 取簡介的前100個字符並加上省略號
                short_intro = intro[:100] + "..." if len(intro) > 100 else intro
                result_lines.append(f"   簡介: {short_intro}\n")

            # 添加設施資訊
            facilities = hotel.get("facilities", [])
            if facilities:
                facilities_str = ", ".join(facilities)
                result_lines.append(f"   設施: {facilities_str}\n")

            # 添加入住和退房時間
            check_in = hotel.get("check_in", "")
            check_out = hotel.get("check_out", "")
            if check_in and check_out:
                result_lines.append(f"   入住: {check_in}, 退房: {check_out}\n")

            # 添加聯絡電話
            phone = hotel.get("phone", "")
            if phone:
                result_lines.append(f"   電話: {phone}\n")

            result_lines.append("\n")

        return "".join(result_lines)

    def _format_plans_for_llm(self, plans: list[dict[str, Any]]) -> str:
        """將方案數據格式化為LLM易於理解的文本"""
        if not plans:
            return ""

        result_lines = []
        for i, plan in enumerate(plans[:3]):  # 限制輸入給LLM的資料數量
            plan_name = plan.get("name", "未知方案")
            hotel_name = plan.get("hotel_name", "未知旅館")
            price = plan.get("price", 0)
            description = plan.get("description", "")

            result_lines.append(f"{i + 1}. {plan_name} - {hotel_name}\n")
            result_lines.append(f"   價格: {price}元\n")

            if description:
                # 取描述的前100個字符並加上省略號
                short_desc = description[:100] + "..." if len(description) > 100 else description
                result_lines.append(f"   描述: {short_desc}\n")

            result_lines.append("\n")

        return "".join(result_lines)

    async def _generate_recommendation_stream(self, llm_input: str, session_id: str) -> str:
        """使用LLM生成旅館推薦並直接流式輸出到前端"""
        try:
            self.logger.info("開始使用LLM生成旅館推薦 (流式輸出)")

            # 構建系統提示 - 明確定義LLM的角色和任務
            system_prompt = """你是旅館推薦助手，根據用戶需求推薦合適旅館。

嚴格遵守以下輸出規則:
1. 使用純文本，完全不使用任何特殊符號或格式標記
2. 設施列表使用逗號分隔，不使用列表格式
3. 參考回覆範例，可自行發揮，但必須依據旅館資料和用戶需求真實描述，不能虛構
4. 最多只提供2間旅館建議，若不是那麼符合，只提供一間最相近，並且要誠實告知建議調整搜索條件。
5. 地址只輸出中文地址。
6. 不提供

回覆格式範例
你好！根據你的需求，我推薦以下幾間旅館:

1. 旅館名稱
- 地址: XX市OO區OO路五段7號
- 價格: 3500元
- 特色: 免費早餐，健身房
- 推薦原因: 推薦原因：高級奢華，提供世界級餐飲與水療服務，適合享受高品質住宿的旅客。

2. 旅館名稱
- 地址: XX市OO區XXXX四段170號
- 價格: 2800元
- 特色: 房間寬敞，有家庭房型
- 推薦原因: 坐落於湖畔，擁有無敵湖景與靜謐環境，適合放鬆度假與享受自然之美。

如果沒有符合需求的旅館，請誠實告知並建議調整搜索條件。
"""

            # 準備消息列表 - 只包含用戶的查詢和旅館資料
            messages = [{"role": "user", "content": llm_input}]

            # 發送開始標記
            await ws_manager.broadcast_chat_message(
                session_id,
                {
                    "role": "assistant_stream_start",
                    "content": "",
                    "timestamp": "",
                },
            )

            # 收集完整回應用於返回
            complete_response = []

            # 用於追蹤是否在思考區塊內
            in_think_block = False
            think_buffer = ""

            # 直接流式處理LLM回應
            async for chunk in llm_agent.stream_response(messages, system_prompt):
                # 檢查是否包含思考標籤
                if "<think>" in chunk:
                    # 分割 chunk，只保留 <think> 之前的部分
                    parts = chunk.split("<think>", 1)
                    if parts[0]:  # 如果 <think> 前有內容
                        complete_response.append(parts[0])
                        await ws_manager.broadcast_chat_message(
                            session_id,
                            {
                                "role": "assistant_stream",
                                "content": parts[0],
                                "timestamp": "",
                            },
                        )
                    in_think_block = True
                    think_buffer = parts[1] if len(parts) > 1 else ""
                    continue

                if in_think_block:
                    if "</think>" in chunk:
                        # 分割 chunk，只保留 </think> 之後的部分
                        parts = chunk.split("</think>", 1)
                        in_think_block = False
                        if len(parts) > 1 and parts[1]:  # 如果 </think> 後有內容
                            complete_response.append(parts[1])
                            await ws_manager.broadcast_chat_message(
                                session_id,
                                {
                                    "role": "assistant_stream",
                                    "content": parts[1],
                                    "timestamp": "",
                                },
                            )
                    else:
                        # 仍在思考區塊內，繼續收集但不發送
                        think_buffer += chunk
                else:
                    # 不在思考區塊內，正常處理
                    complete_response.append(chunk)
                    await ws_manager.broadcast_chat_message(
                        session_id,
                        {
                            "role": "assistant_stream",
                            "content": chunk,
                            "timestamp": "",
                        },
                    )

                # 可選：添加小延遲以控制輸出速度
                await asyncio.sleep(0.01)

            # 發送結束標記
            await ws_manager.broadcast_chat_message(
                session_id,
                {
                    "role": "assistant_stream_end",
                    "content": "",
                    "timestamp": "",
                },
            )

            # 過濾掉思考區塊後的完整回應
            result = "".join(complete_response)
            self.logger.info(f"旅館推薦流式生成完成，回應長度: {len(result)}")
            return result

        except Exception as e:
            self.logger.error(f"流式生成旅館推薦時發生錯誤: {e}")
            # 嘗試發送錯誤消息
            try:
                await ws_manager.broadcast_chat_message(
                    session_id,
                    {
                        "role": "system",
                        "content": f"生成推薦時發生錯誤: {e}",
                        "timestamp": "",
                    },
                )
            except Exception as e2:
                self.logger.error(f"發送錯誤通知也失敗: {e2}")

            return f" 很抱歉，生成旅館推薦時發生錯誤: {e}"


# 創建旅館推薦生成Agent實例
hotel_recommendation_agent = HotelRecommendationAgent()
