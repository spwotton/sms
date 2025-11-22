from sms_hub.db import InMemoryQueue
from sms_hub.jasmin import JasminClient, SmsDispatcher


def test_dispatch_queues_message():
    queue = InMemoryQueue()
    jasmin = JasminClient(queue)
    dispatcher = SmsDispatcher(jasmin)

    payload = dispatcher.dispatch("+15550000001", "Family alert")

    assert payload["status"] == "queued"
    assert queue.all()[0]["body"] == "Family alert"
