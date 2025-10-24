import httpx
import logging
from typing import AsyncGenerator
import json

from .config import settings

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """请分析这张屏幕截图,基于前面的分析历史,**只描述发生的变化和新的活动**:

重点关注:
1. **与前一帧相比的变化**:
   - 如果是第一帧,描述当前状态
   - 如果不是第一帧,只描述与之前不同的内容
   - 代码是否有新增或修改?
   - 窗口或界面是否切换?

2. **当前正在进行的活动**:
   - 正在写代码/调试/查看文档/思考/其他
   - 具体操作(例如:添加了新函数、修改了某行代码、切换到浏览器等)

3. **简洁连贯的描述**:
   - 用自然语言描述这一时刻的活动
   - 不要重复前面已经描述过的内容
   - 保持记录的连贯性和可读性

请用中文以**连贯的叙述方式**回答,避免使用固定格式,就像在记录一个持续的过程。
"""

VIDEO_ANALYSIS_PROMPT_TEMPLATE = """请分析这段视频内容（时间范围：{start_time:.1f}秒 - {end_time:.1f}秒）。

{context_instruction}

分析要求：
1. **描述视频中发生的事情**：
   - 用户在做什么活动？
   - 屏幕上显示了什么内容？
   - 有哪些关键操作或变化？

2. **保持连贯性**：
   - 结合之前的上下文理解当前活动
   - 只描述这个时间段内新发生的事情
   - 避免重复之前已经描述过的内容

3. **输出格式**：
   - 用自然、流畅的中文叙述
   - 就像在记录一个连续的过程
   - 不要使用固定的格式或标题

请开始分析：
"""

class QwenVisionClient:
    def __init__(self):
        self.api_key = settings.qwen_api_key
        self.api_url = settings.qwen_api_url
        self.model = settings.ai_model_name
        self.timeout = settings.timeout_seconds

        if not self.api_key:
            logger.warning("Qwen API key not configured!")

    async def analyze_frame_streaming(
        self,
        base64_image: str,
        context: list[dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Analyze a single frame with streaming response

        Args:
            base64_image: Base64-encoded JPEG image (with or without data URI prefix)
            context: Previous conversation context (optional)

        Yields:
            str: Individual tokens from the AI response
        """
        # Ensure image has data URI prefix
        if not base64_image.startswith("data:image"):
            image_data = f"data:image/jpeg;base64,{base64_image}"
        else:
            image_data = base64_image

        # Build message content
        message_content = [
            {"image": image_data},
            {"text": ANALYSIS_PROMPT}
        ]

        # Include context if provided
        messages = []
        if context:
            messages.extend(context)

        messages.append({
            "role": "user",
            "content": message_content
        })

        # Build request payload
        payload = {
            "model": self.model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "incremental_output": True  # Enable streaming
            }
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    self.api_url,
                    json=payload,
                    headers=headers
                ) as response:
                    response.raise_for_status()

                    # Parse SSE stream
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if not data_str:
                                continue

                            try:
                                data = json.loads(data_str)
                                output = data.get("output", {})
                                choices = output.get("choices", [])

                                if choices and len(choices) > 0:
                                    message = choices[0].get("message", {})
                                    content = message.get("content", [])

                                    # Extract text from content
                                    for item in content:
                                        if isinstance(item, dict) and "text" in item:
                                            yield item["text"]
                                        elif isinstance(item, str):
                                            yield item

                                # Check if finished
                                finish_reason = choices[0].get("finish_reason") if choices else None
                                if finish_reason == "stop":
                                    break

                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse SSE data: {data_str}")
                                continue

        except httpx.HTTPStatusError as e:
            logger.error(f"Qwen API HTTP error: {e.response.status_code} - {e.response.text}")
            yield f"[ERROR] API returned {e.response.status_code}"
        except httpx.TimeoutException:
            logger.error("Qwen API request timed out")
            yield "[ERROR] Request timed out"
        except Exception as e:
            logger.error(f"Unexpected error calling Qwen API: {e}", exc_info=True)
            yield f"[ERROR] {str(e)}"

    async def analyze_frame(self, base64_image: str, context: list[dict] = None) -> str:
        """
        Non-streaming analysis (collect all tokens)
        """
        tokens = []
        async for token in self.analyze_frame_streaming(base64_image, context):
            tokens.append(token)
        return "".join(tokens)

    async def analyze_video_streaming(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        context: list[dict] = None,
        previous_summary: str = None
    ) -> AsyncGenerator[str, None]:
        """
        Analyze a video window with streaming response

        Args:
            video_path: Path to video file or HTTP/HTTPS URL
            start_time: Window start time (seconds)
            end_time: Window end time (seconds)
            context: Previous conversation context (optional)
            previous_summary: Summary of previous windows analysis

        Yields:
            str: Individual tokens from the AI response
        """
        # Build context instruction
        if previous_summary:
            context_instruction = f"之前的分析摘要：{previous_summary}\n\n请基于以上内容，分析当前时间段的新内容。"
        else:
            context_instruction = "这是第一个分析窗口，请完整描述视频内容。"

        # Build prompt with time range and context
        prompt = VIDEO_ANALYSIS_PROMPT_TEMPLATE.format(
            start_time=start_time,
            end_time=end_time,
            context_instruction=context_instruction
        )

        # Build message content
        # Qwen-VL supports both local file:// URLs and HTTP/HTTPS URLs
        if video_path.startswith("http://") or video_path.startswith("https://"):
            # Use HTTP URL directly
            video_url = video_path
        else:
            # Convert local path to file:// URL
            import os
            abs_video_path = os.path.abspath(video_path)
            video_url = f"file://{abs_video_path}"

        message_content = [
            {"video": video_url},
            {"text": prompt}
        ]

        # Include context if provided
        messages = []
        if context:
            messages.extend(context)

        messages.append({
            "role": "user",
            "content": message_content
        })

        # Build request payload
        payload = {
            "model": self.model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "incremental_output": True  # Enable streaming
            }
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable"
        }

        try:
            logger.info(f"Analyzing video window: {start_time:.1f}s - {end_time:.1f}s")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    self.api_url,
                    json=payload,
                    headers=headers
                ) as response:
                    response.raise_for_status()

                    # Parse SSE stream
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if not data_str:
                                continue

                            try:
                                data = json.loads(data_str)

                                output = data.get("output", {})
                                choices = output.get("choices", [])

                                if choices and len(choices) > 0:
                                    message = choices[0].get("message", {})
                                    content = message.get("content", [])

                                    # Extract text from content
                                    for item in content:
                                        if isinstance(item, dict) and "text" in item:
                                            yield item["text"]
                                        elif isinstance(item, str):
                                            yield item

                                # Check if finished
                                finish_reason = choices[0].get("finish_reason") if choices else None
                                if finish_reason == "stop":
                                    break

                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse SSE data: {data_str}")
                                continue

        except httpx.HTTPStatusError as e:
            logger.error(f"Qwen API HTTP error: {e.response.status_code} - {e.response.text}")
            yield f"[ERROR] API returned {e.response.status_code}"
        except httpx.TimeoutException:
            logger.error("Qwen API request timed out")
            yield "[ERROR] Request timed out"
        except Exception as e:
            logger.error(f"Unexpected error calling Qwen API: {e}", exc_info=True)
            yield f"[ERROR] {str(e)}"

    async def analyze_video(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        context: list[dict] = None,
        previous_summary: str = None
    ) -> str:
        """
        Non-streaming video analysis (collect all tokens)
        """
        tokens = []
        async for token in self.analyze_video_streaming(
            video_path, start_time, end_time, context, previous_summary
        ):
            tokens.append(token)
        return "".join(tokens)
