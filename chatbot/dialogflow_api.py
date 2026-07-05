"""
dialogflow_api.py
------------------
Wraps the Google Dialogflow ES API (google-cloud-dialogflow SDK) so the
rest of the application can send a plain text message and receive a
plain text response without worrying about SDK-specific details.

Requires a Dialogflow ES agent and a service account credentials JSON
file. See README.md for full setup instructions.
"""

import logging
import os
import uuid

logger = logging.getLogger(__name__)

try:
    import dialogflow_v2 as dialogflow  # older package name fallback
except ImportError:
    try:
        from google.cloud import dialogflow
    except ImportError:
        dialogflow = None


class DialogflowAPIError(Exception):
    """Raised when communication with Dialogflow fails."""


class DialogflowClient:
    """Client responsible for sending messages to a Dialogflow ES agent."""

    def __init__(self, project_id: str, credentials_path: str,
                 language_code: str = "en"):
        """
        Initialize the Dialogflow session client.

        Args:
            project_id (str): Google Cloud / Dialogflow project ID.
            credentials_path (str): Path to the service account JSON file.
            language_code (str): Language code to use (default "en").
        """
        self.project_id = project_id
        self.language_code = language_code
        self.credentials_path = credentials_path
        self._session_client = None
        self._enabled = False

        self._initialize_client()

    def _initialize_client(self):
        """Set up credentials and the Dialogflow SessionsClient."""
        if dialogflow is None:
            logger.warning(
                "google-cloud-dialogflow is not installed. "
                "Chatbot will run in fallback-only mode."
            )
            return

        if not self.project_id:
            logger.warning(
                "DIALOGFLOW_PROJECT_ID is not set. "
                "Chatbot will run in fallback-only mode."
            )
            return

        if not os.path.exists(self.credentials_path):
            logger.warning(
                "Dialogflow credentials file not found at %s. "
                "Chatbot will run in fallback-only mode.",
                self.credentials_path,
            )
            return

        try:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            self._session_client = dialogflow.SessionsClient()
            self._enabled = True
            logger.info("Dialogflow client initialized for project '%s'", self.project_id)
        except Exception as error:  # noqa: BLE001 - log any SDK init failure
            logger.error("Failed to initialize Dialogflow client: %s", error)
            self._session_client = None
            self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """Whether the Dialogflow client is properly configured and usable."""
        return self._enabled

    @staticmethod
    def generate_session_id() -> str:
        """Generate a new unique session id for a chat conversation."""
        return str(uuid.uuid4())

    def detect_intent(self, session_id: str, text: str) -> dict:
        """
        Send a text message to Dialogflow and return the detected result.

        Args:
            session_id (str): Unique session identifier for the conversation.
            text (str): The user's message.

        Returns:
            dict: {
                "response_text": str,
                "intent": str,
                "confidence": float,
                "is_fallback": bool
            }

        Raises:
            DialogflowAPIError: If the request to Dialogflow fails.
        """
        if not self._enabled:
            return self._fallback_response(text)

        try:
            session = self._session_client.session_path(self.project_id, session_id)
            text_input = dialogflow.types.TextInput(
                text=text, language_code=self.language_code
            )
            query_input = dialogflow.types.QueryInput(text=text_input)

            response = self._session_client.detect_intent(
                session=session, query_input=query_input
            )
            result = response.query_result

            return {
                "response_text": result.fulfillment_text or self._default_fallback_text(),
                "intent": result.intent.display_name,
                "confidence": result.intent_detection_confidence,
                "is_fallback": result.intent.is_fallback,
            }
        except Exception as error:  # noqa: BLE001
            logger.error("Dialogflow detect_intent failed: %s", error)
            raise DialogflowAPIError(str(error)) from error

    def _fallback_response(self, text: str) -> dict:
        """
        Simple rule-based fallback used when Dialogflow is not configured.
        This keeps the app fully functional out-of-the-box for local
        testing before Dialogflow credentials are set up.
        """
        text_lower = text.lower().strip()

        rules = {
            ("hi", "hello", "hey"): "Hello! How can I help you today?",
            ("bye", "goodbye", "see you"): "Goodbye! Have a great day!",
            ("thanks", "thank you"): "You're welcome!",
            ("joke",): "Why do programmers prefer dark mode? Because light attracts bugs!",
            ("weather",): "I can't check live weather yet, but you can ask me anything else!",
            ("your name", "who are you"): "I'm your friendly AI chatbot assistant.",
        }

        for keywords, reply in rules.items():
            if any(keyword in text_lower for keyword in keywords):
                return {
                    "response_text": reply,
                    "intent": "fallback.rule_based",
                    "confidence": 1.0,
                    "is_fallback": False,
                }

        return {
            "response_text": self._default_fallback_text(),
            "intent": "Default Fallback Intent",
            "confidence": 0.0,
            "is_fallback": True,
        }

    @staticmethod
    def _default_fallback_text() -> str:
        return "I'm sorry, I didn't quite understand that. Could you rephrase?"
