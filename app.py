"""
app.py
-------
Main Flask application entry point for the AI Chatbot Using Dialogflow
project.

Routes:
    GET  /        -> Renders the chat UI.
    POST /chat    -> Accepts a user message, returns the bot's reply.
    GET  /history -> Returns stored conversation history for a session.
    POST /clear   -> Clears conversation history for a session.
    GET  /health  -> Simple health check endpoint.
"""

import logging
import os
import uuid

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS

from config import get_config
from chatbot.dialogflow_api import DialogflowClient
from chatbot.chatbot import Chatbot
from database.database import Database

# ---------------------------------------------------------------------------
# App & configuration setup
# ---------------------------------------------------------------------------

config = get_config()

app = Flask(__name__)
app.config.from_object(config)
app.secret_key = config.SECRET_KEY

CORS(app, resources={r"/*": {"origins": config.CORS_ORIGINS}})

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_FILE),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service initialization (database, Dialogflow client, chatbot service)
# ---------------------------------------------------------------------------

database = Database(config.DATABASE_PATH)

dialogflow_client = DialogflowClient(
    project_id=config.DIALOGFLOW_PROJECT_ID,
    credentials_path=config.DIALOGFLOW_CREDENTIALS_PATH,
    language_code=config.DIALOGFLOW_LANGUAGE_CODE,
)

chatbot_service = Chatbot(dialogflow_client=dialogflow_client, database=database)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_or_create_session_id() -> str:
    """Fetch the session id from the Flask session, creating one if absent."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Render the chatbot UI."""
    get_or_create_session_id()
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """
    Accept a JSON payload {"message": "..."} and return the bot's reply.
    """
    try:
        payload = request.get_json(silent=True) or {}
        message = payload.get("message", "")
        session_id = payload.get("session_id") or get_or_create_session_id()

        if not isinstance(message, str) or not message.strip():
            return jsonify({"success": False, "error": "Message cannot be empty."}), 400

        result = chatbot_service.handle_message(session_id, message)
        status_code = 200 if result.get("success") else 502
        return jsonify(result), status_code

    except Exception as error:  # noqa: BLE001
        logger.exception("Unhandled error in /chat: %s", error)
        return jsonify({
            "success": False,
            "error": "An unexpected server error occurred. Please try again.",
        }), 500


@app.route("/history", methods=["GET"])
def history():
    """Return conversation history for the current (or given) session."""
    try:
        session_id = request.args.get("session_id") or get_or_create_session_id()
        records = chatbot_service.get_history(session_id)
        return jsonify({"success": True, "history": records}), 200
    except Exception as error:  # noqa: BLE001
        logger.exception("Unhandled error in /history: %s", error)
        return jsonify({"success": False, "error": "Could not retrieve history."}), 500


@app.route("/clear", methods=["POST"])
def clear():
    """Clear conversation history for the current (or given) session."""
    try:
        payload = request.get_json(silent=True) or {}
        session_id = payload.get("session_id") or get_or_create_session_id()
        success = chatbot_service.clear_history(session_id)
        return jsonify({"success": success}), 200 if success else 500
    except Exception as error:  # noqa: BLE001
        logger.exception("Unhandled error in /clear: %s", error)
        return jsonify({"success": False, "error": "Could not clear history."}), 500


@app.route("/health", methods=["GET"])
def health():
    """Basic health check endpoint used for uptime monitoring."""
    return jsonify({
        "status": "ok",
        "dialogflow_enabled": dialogflow_client.is_enabled,
        "total_conversations": database.get_total_conversations(),
    }), 200


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(_error):
    return jsonify({"success": False, "error": "Resource not found."}), 404


@app.errorhandler(500)
def internal_error(_error):
    return jsonify({"success": False, "error": "Internal server error."}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
