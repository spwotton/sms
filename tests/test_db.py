import sqlite3

from sms_hub.db import DatabaseClient


def setup_contacts(db: DatabaseClient):
    cursor = db._execute(
        "INSERT INTO contacts (name, phone, priority, relationship) VALUES (?, ?, ?, ?)",
        ("Alice", "+15550000001", 1, "parent"),
    )
    cursor.close()
    cursor = db._execute(
        "INSERT INTO contacts (name, phone, priority, relationship) VALUES (?, ?, ?, ?)",
        ("Bob", "+15550000002", 2, "sibling"),
    )
    cursor.close()
    db.connection.commit()


def test_get_contacts_filters_priority_and_relationship():
    conn = sqlite3.connect(":memory:")
    db = DatabaseClient(conn)
    db.ensure_schema()
    setup_contacts(db)

    contacts = db.get_contacts(priority=1, relationship="parent")
    assert len(contacts) == 1
    assert contacts[0]["name"] == "Alice"


def test_queue_message_returns_identifier():
    conn = sqlite3.connect(":memory:")
    db = DatabaseClient(conn)
    db.ensure_schema()
    setup_contacts(db)

    contact_id = db.get_contacts()[0]["id"]
    queued_id = db.queue_message(contact_id, "Hello there")
    assert queued_id >= 1
