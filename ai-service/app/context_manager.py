import logging
from typing import Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Manages conversation context for each session
    Maintains history of interactions to provide context for AI analysis

    For video analysis with sliding windows, also manages:
    - Window-level summaries
    - Previous window context for continuity
    """

    def __init__(self, max_history: int = 10, max_window_summaries: int = 5):
        """
        Args:
            max_history: Maximum number of messages to keep in context (for frame analysis)
            max_window_summaries: Maximum number of window summaries to keep (for video analysis)
        """
        self.max_history = max_history
        self.max_window_summaries = max_window_summaries
        # session_id -> deque of messages (for frame-based analysis)
        self.contexts: Dict[str, deque] = {}
        # session_id -> deque of window summaries (for video analysis)
        self.window_summaries: Dict[str, deque] = {}

    def get_context(self, session_id: str) -> List[dict]:
        """
        Get conversation context for a session

        Returns:
            List of message dictionaries in OpenAI/Qwen format
        """
        if session_id not in self.contexts:
            self.contexts[session_id] = deque(maxlen=self.max_history)
            logger.info(f"Created new context for session {session_id}")

        return list(self.contexts[session_id])

    def add_to_context(self, session_id: str, content: str, role: str = "assistant"):
        """
        Add a message to session context

        Args:
            session_id: Session ID
            content: Message content
            role: Message role (user/assistant)
        """
        if session_id not in self.contexts:
            self.contexts[session_id] = deque(maxlen=self.max_history)

        message = {
            "role": role,
            "content": [{"text": content}]
        }

        self.contexts[session_id].append(message)
        logger.debug(f"Added to context for session {session_id}, total messages: {len(self.contexts[session_id])}")

    def clear_context(self, session_id: str):
        """
        Clear context for a session
        """
        if session_id in self.contexts:
            del self.contexts[session_id]
            logger.info(f"Cleared context for session {session_id}")

    def get_session_count(self) -> int:
        """
        Get number of active sessions
        """
        return len(self.contexts)

    # ========== 视频窗口分析上下文管理 ==========

    def add_window_summary(self, session_id: str, window_index: int, summary: str):
        """
        添加视频窗口的分析摘要

        Args:
            session_id: 会话 ID
            window_index: 窗口索引
            summary: 窗口分析摘要
        """
        if session_id not in self.window_summaries:
            self.window_summaries[session_id] = deque(maxlen=self.max_window_summaries)

        self.window_summaries[session_id].append({
            "window_index": window_index,
            "summary": summary
        })

        logger.info(
            f"Added window {window_index} summary for session {session_id}, "
            f"total summaries: {len(self.window_summaries[session_id])}"
        )

    def get_previous_window_summary(self, session_id: str) -> Optional[str]:
        """
        获取前一个窗口的摘要（用于保持连贯性）

        Returns:
            前一个窗口的摘要，如果没有则返回 None
        """
        if session_id not in self.window_summaries or len(self.window_summaries[session_id]) == 0:
            return None

        # 返回最后一个窗口的摘要
        last_window = self.window_summaries[session_id][-1]
        return last_window["summary"]

    def get_all_window_summaries(self, session_id: str) -> List[dict]:
        """
        获取所有窗口摘要

        Returns:
            窗口摘要列表，每个元素包含 window_index 和 summary
        """
        if session_id not in self.window_summaries:
            return []

        return list(self.window_summaries[session_id])

    def get_compressed_history(self, session_id: str, max_length: int = 500) -> str:
        """
        获取压缩的历史摘要（多个窗口的总结）

        Args:
            session_id: 会话 ID
            max_length: 每个摘要的最大长度（字符数）

        Returns:
            压缩的历史摘要字符串
        """
        summaries = self.get_all_window_summaries(session_id)
        if not summaries:
            return ""

        # 如果只有一个摘要，直接返回
        if len(summaries) == 1:
            return summaries[0]["summary"][:max_length]

        # 多个摘要，拼接前面的（除了最后一个）
        compressed_parts = []
        for window in summaries[:-1]:
            # 截断每个摘要以避免过长
            compressed_parts.append(f"[窗口{window['window_index']}] {window['summary'][:max_length]}")

        return " -> ".join(compressed_parts)

    def clear_window_summaries(self, session_id: str):
        """
        清空会话的窗口摘要

        Args:
            session_id: 会话 ID
        """
        if session_id in self.window_summaries:
            del self.window_summaries[session_id]
            logger.info(f"Cleared window summaries for session {session_id}")
