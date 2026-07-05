"""
chatbot.py
-----------
Business logic layer that ties together the Dialogflow client and the
database layer. This is the single entry point the Flask routes call
into, keeping app.py thin and focused on HTTP concerns only.
"""

import logging

from chatbot.dialogflow_api import DialogflowClient, DialogflowAPIError
from database.database import Database

logger = logging.getLogger(__name__)


class Chatbot:
    """High level chatbot service combining NLU and persistence."""

    def __init__(self, dialogflow_client: DialogflowClient, database: Database):
        self.dialogflow_client = dialogflow_client
        self.database = database

    def handle_message(self, session_id: str, message: str) -> dict:
        """
        Process an incoming user message end-to-end.

        Args:
            session_id (str): The chat session identifier.
            message (str): The raw text sent by the user.

        Returns:
            dict: Structured payload ready to be returned as JSON.
        """
        message = (message or "").strip()

        if not message:
            return {
                "success": False,
                "error": "Message cannot be empty.",
            }

        try:
            result = self.dialogflow_client.detect_intent(session_id, message)
        except DialogflowAPIError as error:
            logger.error("Dialogflow failure while handling message: %s", error)
            return {
                "success": False,
                "error": "The chatbot service is temporarily unavailable. Please try again shortly.",
            }
        except Exception as error:  # noqa: BLE001
            logger.exception("Unexpected error while handling message: %s", error)
            return {
                "success": False,
                "error": "Something went wrong while processing your message.",
            }

        try:
            self.database.save_conversation(
                session_id=session_id,
                user_message=message,
                bot_response=result["response_text"],
                intent=result.get("intent"),
            )
        except Exception as error:  # noqa: BLE001
            # A database failure shouldn't prevent the user from getting a reply.
            logger.error("Failed to persist conversation: %s", error)

        return {
            "success": True,
            "response": result["response_text"],
            "intent": result.get("intent"),
            "is_fallback": result.get("is_fallback", False),
        }

    def get_history(self, session_id: str) -> list:
        """Return the stored conversation history for a session."""
        try:
            return self.database.get_history(session_id)
        except Exception as error:  # noqa: BLE001
            logger.error("Failed to retrieve history: %s", error)
            return []

    def clear_history(self, session_id: str) -> bool:
        """Clear the stored conversation history for a session."""
        try:
            self.database.clear_history(session_id)
            return True
        except Exception as error:  # noqa: BLE001
            logger.error("Failed to clear history: %s", error)
            return False
