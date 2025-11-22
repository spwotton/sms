"""Database helpers for the SMS hub.

MySQL 8.0 schema reference::

    CREATE TABLE IF NOT EXISTS contacts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        phone VARCHAR(20) NOT NULL UNIQUE,
        priority TINYINT NOT NULL DEFAULT 5,
        relationship VARCHAR(64) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        contact_id INT NOT NULL,
        body TEXT NOT NULL,
        status VARCHAR(32) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
    );

The code intentionally uses parameterized queries to prevent injection.
"""

from typing import Any, Dict, Iterable, List, Optional


class DatabaseClient:
    def __init__(self, connection):
        self.connection = connection
        self.placeholder = "%s"
        module_name = getattr(connection, "__module__", "")
        if module_name.startswith("sqlite3"):
            self.placeholder = "?"
            connection.row_factory = getattr(connection, "Row", None)

    def _execute(self, query: str, params: Iterable[Any] = ()):  # type: ignore[assignment]
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor

    def get_contacts(self, priority: Optional[int] = None, relationship: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT id, name, phone, priority, relationship FROM contacts WHERE 1=1"
        params: List[Any] = []
        if priority is not None:
            query += f" AND priority = {self.placeholder}"
            params.append(priority)
        if relationship is not None:
            query += f" AND relationship = {self.placeholder}"
            params.append(relationship)
        query += " ORDER BY priority ASC, name ASC"

        cursor = self._execute(query, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def queue_message(self, contact_id: int, body: str) -> int:
        query = (
            "INSERT INTO messages (contact_id, body, status) "
            f"VALUES ({self.placeholder}, {self.placeholder}, {self.placeholder})"
        )
        cursor = self._execute(query, (contact_id, body, "queued"))
        self.connection.commit()
        return getattr(cursor, "lastrowid", cursor.lastrowid if cursor else 0)

    def ensure_schema(self):
        cursor = self._execute(
            "CREATE TABLE IF NOT EXISTS contacts ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "name TEXT NOT NULL,"
            "phone TEXT NOT NULL UNIQUE,"
            "priority INTEGER NOT NULL DEFAULT 5,"
            "relationship TEXT NOT NULL"
            ")"
        )
        cursor.close()
        cursor = self._execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "contact_id INTEGER NOT NULL,"
            "body TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
            "FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE CASCADE"
            ")"
        )
        cursor.close()
        self.connection.commit()


class InMemoryQueue:
    def __init__(self):
        self._items: List[Dict[str, Any]] = []

    def add(self, item: Dict[str, Any]) -> None:
        self._items.append(item)

    def all(self) -> List[Dict[str, Any]]:
        return list(self._items)
