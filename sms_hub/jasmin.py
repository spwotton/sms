from typing import Any, Dict, List

from sms_hub.db import InMemoryQueue


class JasminClient:
    """Lightweight Jasmin SMS Gateway integration stub."""

    def __init__(self, queue: InMemoryQueue):
        self.queue = queue

    def send(self, phone: str, body: str) -> Dict[str, Any]:
        payload = {"to": phone, "body": body, "status": "queued"}
        self.queue.add(payload)
        return payload


class SmsDispatcher:
    def __init__(self, jasmin_client: JasminClient):
        self.jasmin_client = jasmin_client

    def dispatch(self, phone: str, body: str) -> Dict[str, Any]:
        return self.jasmin_client.send(phone, body)
