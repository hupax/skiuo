import logging
from typing import Dict, List
from collections import deque

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Manages conversation context for each session
    Maintains history of interactions to provide context for AI analysis
    """

    def __init__(self, max_history: int = 10):
        """
        Args:
            max_history: Maximum number of messages to keep in context
        """
        self.max_history = max_history
        # session_id -> deque of messages
        self.contexts: Dict[str, deque] = {}

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
