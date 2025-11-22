# **Ψ-Coherence Hub MySQL Adaptation: Design Document**  
**Version 1.0** | **Date: 2025-02-14**  

---

## **1. Executive Summary**  
This document details the Ψ-Coherence Hub migration to MySQL with a focus on **security**, **performance**, **scalability**, and **operational reliability**. Enhancements include parameterized queries, targeted indexing, TLS-encrypted DB channels, TTL-based caching with schema-version keys, observability via Grafana, and automated (yet isolated) backup jobs. The solution aligns with cloud security and performance guidelines (AWS, Google Cloud) while staying lightweight for the project’s footprint.

---

## **2. Introduction**  
### **2.1 Background**  
- Ψ-Coherence Hub coordinates contact management with SMS/email workflows.  
- PostgreSQL foundations were ported to MySQL to match the existing Ops skillset and infrastructure.  

### **2.2 Goals**  
- **Security**: Eliminate SQL injection vectors, enforce least privilege, and encrypt data in transit.  
- **Performance**: Optimize read-heavy contact retrieval paths and reduce DB round-trips.  
- **Maintainability**: Provide a deterministic deployment path and simplified day-2 operations.  

---

## **3. System Architecture Overview**  
### **3.1 High-Level Components**  
1. **Frontend** — React SPA for contact/message management.  
2. **Backend** — Python/Flask API exposing `/messages`, `/recipients`, etc.  
3. **Database** — MySQL 8.0 storing contacts, logs, and auth data.  
4. **Supporting Services** — Jasmin SMS gateway, Grafana observability stack, backup sidecar.  

### **3.2 Data Flow Diagram (DFD)**  
```
[Frontend] → [/messages API] → [CoherenceService] → [MySQLMessageRepository] → [MySQL DB]
              ↘ LLM Service (Gemini/OpenAI) ↙   ↘ Validation / Caching ↙
```

---

## **4. Database Design**  
### **4.1 Schema Definition**  
| Table         | Columns (Highlights)                                                                 |
|---------------|---------------------------------------------------------------------------------------|
| `contacts`    | `id` PK, `first_name`, `last_name`, `phone` UNIQUE, `relationship` ENUM, `priority` TINYINT |
| `message_log` | `id` PK, `contact_id` FK, `raw_text`, `processed_text`, `coherence_score` ENUM, `status` ENUM, `sent_at` |
| `users`       | `id` PK, `username` UNIQUE, `password_hash`, `is_admin` |

- `message_log.contact_id` → `contacts.id` (ON DELETE CASCADE).  
- Phone numbers validated via application regex before insert/update.  

### **4.2 Indexing Strategy**  
```sql
CREATE INDEX idx_contacts_priority ON contacts (priority DESC, first_name ASC);
CREATE INDEX idx_contacts_relationship ON contacts (relationship);
CREATE INDEX idx_message_contact_status ON message_log (contact_id, status);
```
**Rationale**: Mirrors access paths from `get_recipients()` (priority ordering, relationship filtering) and message status lookups.

### **4.3 Schema Migration**  
```sql
-- coherence_hub_schema.sql
CREATE DATABASE IF NOT EXISTS coherence_hub
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE coherence_hub;

-- [Table definitions, constraints, indexes...]
```
- Deploy via `mysql -u root -p < coherence_hub_schema.sql`.  
- Track migrations with version control plus `mysqldump` for schema diffs.

---

## **5. Application Design**  
### **5.1 Repository Pattern**  
```python
class MySQLMessageRepository(BaseMessageRepository):
    def __init__(self, connector: MySQLConnection):
        self.conn = connector

    def get_recipients(self, group_filter=None):
        return self.conn.get_recipients(group_filter)

    def log_message(self, contact_id, raw_text, processed_text, score, status):
        query = """
            INSERT INTO message_log (contact_id, raw_text, processed_text, coherence_score, status)
            VALUES (%s, %s, %s, %s, %s)
        """
        self.conn.execute(query, (contact_id, raw_text, processed_text, score, status))
```
- All repository calls rely on parameterized queries to neutralize injection attempts.

### **5.2 Input Validation (Pydantic)**  
```python
import re
from pydantic import BaseModel, field_validator

class ContactInfo(BaseModel):
    phone: str

    @field_validator('phone')
    def validate_phone(cls, v):
        if not re.match(r'^\+\d{10,15}$', v):
            raise ValueError('Invalid E.164 phone number format')
        return v

class MessageInput(BaseModel):
    raw_text: constr(min_length=10, max_length=2000)
    recipient: ContactInfo
```

### **5.3 Recipient Cache**  
```python
from cachetools import TTLCache

class RecipientCache:
    SCHEMA_VERSION = "1.0"

    def __init__(self, repo, cache_ttl=300):
        self.repo = repo
        self.cache = TTLCache(maxsize=500, ttl=cache_ttl)

    def get_recipients(self, group_filter=None):
        key = f"recipients_{group_filter or 'all'}_v{self.SCHEMA_VERSION}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        fresh = self.repo.get_recipients(group_filter)
        self.cache[key] = fresh
        return fresh
```
- TTL refresh plus schema-version key prevents stale data across schema changes.  
- Optionally pre-warm hot cohorts at startup.

### **5.4 Service Layer**  
```python
class CoherenceService:
    def __init__(self, repo, validator, llm, cache):
        self.repo = repo
        self.validator = validator
        self.llm = llm
        self.cache = cache

    def fetch_recipients(self, group_filter=None):
        return self.cache.get_recipients(group_filter)

    def process_message(self, input_data: MessageInput):
        validated = self.validator.validate(input_data.model_dump())
        llm_result = self.llm.process_text(validated["raw_text"])
        self.repo.log_message(
            contact_id=validated["recipient_id"],
            raw_text=validated["raw_text"],
            processed_text=llm_result["text"],
            score=llm_result["score"],
            status="processed",
        )
        return llm_result
```

---

## **6. Security Design**  
### **6.1 Authentication & Authorization**  
- **DB User**: Create `coherence_user` limited to `coherence_hub` schema (`SELECT/INSERT/UPDATE/DELETE`).  
- **App Layer**: RBAC via `users.is_admin`; tokens scoped per user role.

### **6.2 Data Protection**  
- Enable TLS in MySQL (`ALTER INSTANCE ENABLE SSL;`) and mount CA/client certs into the container.  
- **Environment secrets** reside in `.env` or Docker secrets; avoid inline shell substitution (Compose does not execute `$(...)`).  
- Use `mysql_native_password` or `caching_sha2_password` per client compatibility, ensuring strong passwords (≥32 chars, random).

### **6.3 Input Sanitization**  
- Parameterized SQL calls everywhere.  
- Regex-enforced phone/email formats before hitting repositories.  
- Reject unsupported `group_filter` values at the API boundary.

---

## **7. Performance & Scalability**  
### **7.1 Connection Pooling**  
```python
from mysql.connector import pooling

class MySQLConnection:
    def __init__(self):
        self.pool = pooling.MySQLConnectionPool(
            pool_name="coherence_pool",
            pool_size=8,
            pool_reset_session=True,
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'coherence_user'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'coherence_hub'),
            autocommit=True,
        )

    def get_recipients(self, group_filter=None):
        with self.pool.get_connection() as conn:
            cursor = conn.cursor(dictionary=True, buffered=True)
            # ... query shown earlier ...
```
- Increase pool size as parallelism grows; monitor via Grafana.

### **7.2 Query Optimization**  
- Run `EXPLAIN` after migrations to verify index uptake.  
- Consolidate queries (avoid N+1) by batching relationships and eager-loading when necessary.

### **7.3 Backup & Recovery**  
- Dedicated **backup sidecar** container with cron-like schedule:
```yaml
services:
  mysql-backup:
    image: bitnami/mysqldump
    environment:
      MYSQL_HOST: db
      MYSQL_USER: coherence_user
      MYSQL_PASSWORD: ${DB_PASSWORD}
      MYSQL_DATABASE: coherence_hub
      CRON_SCHEDULE: "0 3 * * *"
      MYSQLDUMP_OPTIONS: "--single-transaction --routines"
    volumes:
      - mysql_backups:/backups
    depends_on:
      - db
```
- Retention: `find /backups -mtime +7 -delete`.  
- Periodically test restore drills from backup artifacts.

---

## **8. Monitoring & Observability**  
### **8.1 Metrics**  
- Monitor DB throughput, connection count, slow queries (`performance_schema.events_statements_summary_by_digest`).  
- Capture cache hit/miss counters via custom Prometheus metrics or logs.

### **8.2 Logging**  
- Structured JSON logs using Python `logging` + `structlog`. Include request ID, user ID, status code, latency.

### **8.3 Grafana Dashboards**  
```yaml
services:
  grafana:
    image: supabase/supabase-grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - db
```
**Sample panel query (MySQL data source):**
```sql
SELECT
  EVENT_TIME AS timestamp,
  CURRENT_SCHEMA AS schema_name,
  DIGEST_TEXT AS query_sample,
  TIMER_WAIT/1000000000000 AS duration_ms,
  ROWS_EXAMINED
FROM performance_schema.events_statements_history_long
WHERE EVENT_NAME = 'statement/sql/select'
  AND TIMER_WAIT > 200000000000; -- >200 ms
```
- Add alert rules for slow-query spikes, rising error counts, and failed backups.

---

## **9. Deployment & Operations**  
### **9.1 Environment Setup (Bare Metal / VM)**  
```bash
sudo apt-get update
sudo apt-get install -y mysql-server
sudo systemctl enable --now mysql
sudo mysql_secure_installation  # Set root pwd, remove anonymous users, disable remote root
```

### **9.2 Docker Compose Highlights**  
```yaml
services:
  db:
    image: mysql:8.0
    command: --default-authentication-plugin=mysql_native_password
    env_file: .env
    environment:
      MYSQL_DATABASE: coherence_hub
      MYSQL_USER: coherence_user
      MYSQL_PASSWORD: ${DB_PASSWORD}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_SSL_CA: /certs/ca.pem
      MYSQL_SSL_CERT: /certs/client-cert.pem
      MYSQL_SSL_KEY: /certs/client-key.pem
    volumes:
      - mysql_data:/var/lib/mysql
      - ./certs:/certs:ro
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
```
- Backend and other services consume DB credentials from `.env`; `.env` excluded via `.gitignore`.

### **9.3 Deployment Checklist**  
1. Install MySQL + apply `mysql_secure_installation`.  
2. Generate TLS certs (CA, server, client) and configure MySQL `ssl_ca`, `ssl_cert`, `ssl_key`.  
3. Create `coherence_user` and grant privileges:  
   ```sql
   CREATE USER 'coherence_user'@'%' IDENTIFIED BY '********';
   GRANT SELECT, INSERT, UPDATE, DELETE ON coherence_hub.* TO 'coherence_user'@'%';
   FLUSH PRIVILEGES;
   ```
4. Import schema:  
   ```bash
   mysql -u coherence_user -p coherence_hub < coherence_hub_schema.sql
   ```
5. Run `SHOW INDEX FROM contacts;` to confirm new indexes.  
6. `docker compose up -d --build` (with `.env` present).  
7. Verify Grafana connectivity and TLS enforcement.  

---

## **10. Testing Strategy**  
### **10.1 Unit Tests**  
```python
def test_process_message_logs_once(mocker):
    repo = mocker.Mock()
    validator = mocker.Mock(return_value={"recipient_id": 1, "raw_text": "Hello family"})
    llm = mocker.Mock(return_value={"text": "Processed", "score": "high"})
    cache = mocker.Mock()
    service = CoherenceService(repo, validator, llm, cache)

    service.process_message(MessageInput(raw_text="Hello family", recipient={"phone": "+15555555555"}))

    repo.log_message.assert_called_once()
    validator.validate.assert_called_once()
```

### **10.2 Integration Tests**  
- Use Docker-based test harness hitting `/messages` endpoint with a seeded MySQL instance.  
- Validate entire pipeline: request → validation → LLM stub → DB write.

### **10.3 Performance Tests**  
- Locust scenario simulating 1000 concurrent senders, measuring P95 latency and DB connection saturation.  
- Profiling insights feed adjustments to pool size, cache TTL, and indexes.

---

## **11. Maintenance & Upgrades**  
- Adopt migration tooling (Alembic, Flyway) for versioned DDL.  
- Schedule monthly reviews of slow-query logs and Grafana alerts.  
- Tune cache TTL/schema version upon schema changes.  
- Periodically rotate DB credentials and TLS certs; update `.env` securely.

---

## **12. Conclusion**  
The MySQL-based Ψ-Coherence Hub now delivers a secure, performant, and maintainable platform with hardened authentication, index-backed queries, schema-aware caching, and observable operations. Future roadmap items include SMTP email extensions, Redis-backed distributed caching, and expanded RBAC policies.

---

## **Appendices**  
- **Appendix A** — Sample SQL Scripts (schema, indexes, grants).  
- **Appendix B** — Docker Compose & `.env` templates.  
- **Appendix C** — Pydantic Models and Validators.  
- **Appendix D** — Grafana Dashboard JSON (slow queries, backups, cache metrics).  
- **Appendix E** — Detailed Deployment & Rollback Procedures.  

---

**Approvals**  
- [ ] Technical Lead  
- [ ] Security Team  
- [ ] Operations Team  

**Revision History**  
| Version | Date       | Changes Made        | Author        |
|---------|------------|---------------------|---------------|
| 1.0     | 2025-02-14 | Initial Release     | GPT-5.1-Codex |

---  
**Document End**

## Quickstart (Flask SMS Hub)

This repository now includes a lightweight Flask implementation of the family SMS hub described above. Key capabilities:

- JWT-protected endpoints with rate limiting (10/minute by default).
- Heuristic message stabilization with optional LLM handoff (OpenAI/Gemini).
- Parameterized MySQL-ready queries for contact lookup and message queueing.
- Jasmin Gateway dispatch stub using an in-memory queue for local testing.

### MySQL Environment Variables

Set these variables for a real MySQL deployment:

- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- `SECRET_KEY` (JWT signing), `SYSTEM_USERNAME`, `SYSTEM_PASSWORD`
- `OPENAI_API_KEY`, `GEMINI_API_KEY` (optional LLM integrations)

### Running with Docker

```bash
docker build -t sms-hub .
docker run -p 5000:5000 \
  -e DB_HOST=mysql \
  -e DB_USER=sms_user \
  -e DB_PASSWORD=secret \
  -e DB_NAME=sms_hub \
  -e SECRET_KEY=supersecret \
  -e SYSTEM_USERNAME=family-admin \
  -e SYSTEM_PASSWORD=change-me \
  sms-hub
```

### Core Endpoints

- `POST /api/token` – obtain JWT using `username`/`password` body.
- `POST /api/process` – body `{ "text": "..." }` → classification + stabilized text.
- `GET /api/contacts` – query params `priority`, `relationship` to filter.
- `POST /api/send` – body `{ "phone": "+15551234567", "message": "..." }` to queue via Jasmin stub.
- `GET /health` – health probe.

### Tests

Run unit tests with:

```bash
pytest
```
