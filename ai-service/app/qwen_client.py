import httpx
import logging
from typing import AsyncGenerator
import json

from .config import settings

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """请详细分析这张屏幕截图,重点关注:

1. **屏幕内容识别**:
   - 是否能看到代码?如果能,是什么编程语言?
   - 使用的是什么IDE或编辑器?
   - 能看到的代码片段内容(如果可读)

2. **当前活动判断**:
   - 正在写代码/调试/查看文档/思考/其他
   - 具体在做什么(例如:定义函数、写循环、修复bug等)

3. **详细描述**:
   - 屏幕上可见的所有重要信息
   - 窗口布局和内容
   - 任何值得注意的细节

请用中文回答,格式如下:

【内容识别】
- 编程语言:
- 开发工具:
- 代码内容:

【当前活动】
- 活动类型:
- 具体操作:

【详细描述】
(详细描述屏幕上看到的所有内容)
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
