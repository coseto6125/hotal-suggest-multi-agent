"""
旅館推薦生成Agent，負責生成LLM推薦回應，並支持流式輸出
"""

import asyncio
from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent
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
        conversation_id = state.get("conversation_id", "")

        # 如果沒有旅館資料，直接返回
        if not hotel_details:
            self.logger.warning("沒有旅館資料可供推薦")
            return state

        # 準備LLM輸入
        llm_input = self._prepare_llm_input(query, hotel_details)

        # 呼叫LLM生成推薦並直接流式輸出到前端
        recommendation = ""
        if conversation_id:
            recommendation = await self._generate_recommendation_stream(llm_input, conversation_id)
        else:
            # 如果沒有conversation_id，則使用非流式方式
            recommendation = await self._generate_recommendation(llm_input)

        # 返回結果
        return {
            **state,
            "recommendation": recommendation,
        }

    def _prepare_llm_input(self, query: str, hotel_details: list[str]) -> str:
        """準備LLM輸入"""
        prompt_lines = []
        prompt_lines.append(f"用戶提問需求: {query}\n\n")

        # 添加旅館資料
        if hotel_details:
            prompt_lines.append("旅館資料:\n")
            prompt_lines.append(f"```\n{hotel_details['hotels']}\n```\n")

        # 添加指示
        prompt_lines.append("請根據用戶提問需求和提供的旅館資料，生成一個簡短的旅館推薦。推薦應該包括：\n")
        prompt_lines.append("1. 最適合用戶需求的2-3間旅館\n")
        prompt_lines.append("2. 以用戶需求來看，為何推薦這些旅館\n")
        prompt_lines.append("3. 這個旅館的特色和特點有甚麼其他值得推薦的\n")
        prompt_lines.append("請使用自然、友善的語氣，並保持簡潔。\n")
        prompt_lines.append("請使用繁體中文，並根據旅館資料確實回答，不要回覆不在旅館資料內的額外資訊。\n")

        return "".join(prompt_lines)

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
            if county:
                county_name = county.get("name", "")
                if county_name:
                    result_lines.append(f"   所在縣市: {county_name}\n")

            district = hotel.get("district", {})
            if district:
                district_name = district.get("name", "")
                if district_name:
                    result_lines.append(f"   所在鄉鎮區: {district_name}\n")

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
                result_lines.append(f"   熱門設施: {facilities_str}\n")

            # 添加入住和退房時間
            check_in = hotel.get("check_in", "")
            check_out = hotel.get("check_out", "")
            if check_in and check_out:
                result_lines.append(f"   入住時間: {check_in}, 退房時間: {check_out}\n")

            # 添加聯絡電話
            phone = hotel.get("phone", "")
            if phone:
                result_lines.append(f"   聯絡電話: {phone}\n")

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

            result_lines.append(f"{i + 1}. {plan_name} ({hotel_name})\n")
            result_lines.append(f"   價格: {price} 元\n")

            if description:
                # 取描述的前100個字符並加上省略號
                short_desc = description[:100] + "..." if len(description) > 100 else description
                result_lines.append(f"   描述: {short_desc}\n")

            result_lines.append("\n")

        return "".join(result_lines)

    async def _generate_recommendation(self, llm_input: str) -> str:
        """使用LLM生成旅館推薦 (非流式版本)"""
        try:
            self.logger.info("開始使用LLM生成旅館推薦")

            # 構建系統提示
            system_prompt = """
            你是一個專業的旅館推薦助手，負責為用戶提供旅館推薦和旅遊建議。
            請根據提供的旅館數據和用戶查詢，生成一個全面、有用且引人入勝的回應。
            
            回應應包括：
            1. 對用戶查詢的簡短總結和理解
            2. 推薦的旅館列表，包括：
               - 名稱和地址
               - 價格（如有提供）
               - 為什麼推薦該旅館（基於設施、位置、價格等）
               - 特色和賣點
            3. 簡短的住宿建議或提示
            
            使用友好、專業的語氣，確保信息準確且條理清晰。
            如用戶有特殊要求，請重點說明符合這些要求的旅館。
            避免重複旅館的完整細節，因為用戶已經能夠在界面上查看這些資訊。
            """

            # 準備消息列表
            messages = [{"role": "user", "content": llm_input}]

            # 呼叫LLM服務
            from src.services.llm_service import llm_service

            response_chunks = []
            async for chunk in llm_service.stream_response(messages, system_prompt):
                response_chunks.append(chunk)

            complete_response = "".join(response_chunks)
            self.logger.info(f"旅館推薦生成完成，回應長度: {len(complete_response)}")
            return complete_response

        except Exception as e:
            self.logger.error(f"生成旅館推薦時發生錯誤: {e}")
            return f"很抱歉，生成旅館推薦時發生錯誤: {e}"

    async def _generate_recommendation_stream(self, llm_input: str, conversation_id: str) -> str:
        """使用LLM生成旅館推薦並直接流式輸出到前端"""
        try:
            self.logger.info("開始使用LLM生成旅館推薦 (流式輸出)")

            # 構建系統提示
            system_prompt = """
            你是一個專業的旅館推薦助手，負責為用戶提供旅館推薦和旅遊建議。
            請根據提供的旅館數據和用戶查詢，生成一個全面、有用且引人入勝的回應。
            
            回應應包括：
            1. 推薦的旅館列表，包括：
               - 名稱和地址
               - 價格（如有提供）
               - 為什麼推薦該旅館（基於設施、位置、價格等）
               - 特色和賣點
            2. 簡短的住宿建議或提示
            
            使用友好、專業的語氣，確保信息準確且條理清晰。
            如用戶有特殊要求，請重點說明符合這些要求的旅館。
            避免重複旅館的完整細節，因為用戶已經能夠在界面上查看這些資訊。
            """

            # 準備消息列表
            messages = [{"role": "user", "content": llm_input}]

            # 呼叫LLM服務
            from src.services.llm_service import llm_service

            # 發送開始標記
            await ws_manager.broadcast_chat_message(
                conversation_id,
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
            async for chunk in llm_service.stream_response(messages, system_prompt):
                # 檢查是否包含思考標籤
                if "<think>" in chunk:
                    # 分割 chunk，只保留 <think> 之前的部分
                    parts = chunk.split("<think>", 1)
                    if parts[0]:  # 如果 <think> 前有內容
                        complete_response.append(parts[0])
                        await ws_manager.broadcast_chat_message(
                            conversation_id,
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
                                conversation_id,
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
                        conversation_id,
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
                conversation_id,
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
                    conversation_id,
                    {
                        "role": "system",
                        "content": f"生成推薦時發生錯誤: {e}",
                        "timestamp": "",
                    },
                )
            except Exception as e2:
                self.logger.error(f"發送錯誤通知也失敗: {e2}")

            return f"很抱歉，生成旅館推薦時發生錯誤: {e}"


# 創建旅館推薦生成Agent實例
hotel_recommendation_agent = HotelRecommendationAgent()
