from datetime import datetime
import re
from typing import Any, Dict, Optional

import jwt
import mysql.connector
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from sms_hub.classifier import MessageClassifier
from sms_hub.config import Config
from sms_hub.db import DatabaseClient, InMemoryQueue
from sms_hub.jasmin import JasminClient, SmsDispatcher


PHONE_REGEX = re.compile(r"^\+?\d{7,15}$")


def sanitize_text(value: str) -> str:
    return re.sub(r"[^\w\s.,!?+-]", "", value).strip()


def create_app(config_object: Optional[type] = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    limiter = Limiter(get_remote_address, app=app, default_limits=[app.config["RATE_LIMIT"]])

    queue = InMemoryQueue()
    jasmin_client = JasminClient(queue)
    dispatcher = SmsDispatcher(jasmin_client)
    classifier = MessageClassifier()

    def _authenticate(username: str, password: str) -> bool:
        return (
            username == app.config["DEFAULT_SYSTEM_USER"]
            and password == app.config["DEFAULT_SYSTEM_PASSWORD"]
        )

    def _decode_token(token: str) -> Dict[str, Any]:
        return jwt.decode(token, app.config["SECRET_KEY"], algorithms=[app.config["JWT_ALGORITHM"]])

    def _jwt_required() -> Optional[Dict[str, Any]]:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ", 1)[1]
        try:
            payload = _decode_token(token)
        except jwt.PyJWTError:
            return None
        return payload

    def _build_db_client() -> DatabaseClient:
        if app.config.get("TESTING"):
            from sqlite3 import connect

            sqlite_conn = connect(":memory:")
            db_client = DatabaseClient(sqlite_conn)
            db_client.ensure_schema()
            return db_client
        try:
            mysql_conn = mysql.connector.connect(
                host=app.config["DB_HOST"],
                port=app.config["DB_PORT"],
                user=app.config["DB_USER"],
                password=app.config["DB_PASSWORD"],
                database=app.config["DB_NAME"],
                autocommit=True,
            )
            return DatabaseClient(mysql_conn)
        except mysql.connector.Error:
            from sqlite3 import connect

            sqlite_conn = connect(":memory:")
            db_client = DatabaseClient(sqlite_conn)
            db_client.ensure_schema()
            return db_client

    @app.route("/api/token", methods=["POST"])
    def token():
        data = request.get_json(force=True, silent=True) or {}
        username = sanitize_text(str(data.get("username", "")))
        password = data.get("password", "")
        if not _authenticate(username, password):
            return jsonify({"error": "invalid credentials"}), 401
        payload = {
            "sub": username,
            "exp": datetime.utcnow() + app.config["ACCESS_TOKEN_EXPIRES"],
        }
        encoded = jwt.encode(payload, app.config["SECRET_KEY"], algorithm=app.config["JWT_ALGORITHM"])
        return jsonify({"access_token": encoded})

    def _require_auth():
        claims = _jwt_required()
        if not claims:
            return jsonify({"error": "unauthorized"}), 401
        return claims

    @app.route("/api/process", methods=["POST"])
    @limiter.limit("10 per minute")
    def process_text():
        claims = _require_auth()
        if isinstance(claims, tuple):
            return claims

        data = request.get_json(force=True, silent=True) or {}
        raw_text = sanitize_text(str(data.get("text", "")))
        if not raw_text:
            return jsonify({"error": "text is required"}), 400

        result = classifier.classify(raw_text)
        return jsonify(
            {
                "classification": result["classification"],
                "stabilized_text": result["stabilized_text"],
                "rationale": result["rationale"],
            }
        )

    @app.route("/api/contacts", methods=["GET"])
    @limiter.limit("10 per minute")
    def contacts():
        claims = _require_auth()
        if isinstance(claims, tuple):
            return claims

        db_client = _build_db_client()
        priority = request.args.get("priority")
        relationship = request.args.get("relationship")
        contacts = db_client.get_contacts(
            priority=int(priority) if priority is not None else None,
            relationship=sanitize_text(relationship) if relationship else None,
        )
        return jsonify({"contacts": contacts})

    @app.route("/api/send", methods=["POST"])
    @limiter.limit("10 per minute")
    def send_sms():
        claims = _require_auth()
        if isinstance(claims, tuple):
            return claims

        data = request.get_json(force=True, silent=True) or {}
        phone = sanitize_text(str(data.get("phone", "")))
        message = sanitize_text(str(data.get("message", "")))
        contact_id = data.get("contact_id")

        if not PHONE_REGEX.match(phone):
            return jsonify({"error": "Invalid phone number."}), 400
        if not message:
            return jsonify({"error": "Message body is required."}), 400

        result = dispatcher.dispatch(phone, message)

        if contact_id is not None:
            db_client = _build_db_client()
            db_client.queue_message(int(contact_id), message)

        return jsonify({"queued": True, "gateway": result})

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

    return app
