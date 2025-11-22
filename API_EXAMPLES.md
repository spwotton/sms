# API Examples

## cURL Examples

### 1. Login and Get Token
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer"
}
```

### 2. Create a Contact
```bash
TOKEN="your_access_token_here"

curl -X POST http://localhost:5000/api/contacts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "phone": "+1234567890",
    "priority": "high",
    "relationship": "parent"
  }'
```

### 3. Get All Contacts
```bash
curl -X GET http://localhost:5000/api/contacts \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Send an SMS
```bash
curl -X POST http://localhost:5000/api/sms/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+1234567890",
    "content": "Hello! This is a test message."
  }'
```

### 5. Get Messages
```bash
# Get all messages
curl -X GET http://localhost:5000/api/messages \
  -H "Authorization: Bearer $TOKEN"

# Get only critical messages
curl -X GET "http://localhost:5000/api/messages?classification=critical" \
  -H "Authorization: Bearer $TOKEN"

# Get messages with limit
curl -X GET "http://localhost:5000/api/messages?limit=50" \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Update a Contact
```bash
curl -X PUT http://localhost:5000/api/contacts/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe Updated",
    "priority": "critical"
  }'
```

### 7. Delete a Contact
```bash
curl -X DELETE http://localhost:5000/api/contacts/1 \
  -H "Authorization: Bearer $TOKEN"
```

### 8. Get System Statistics
```bash
curl -X GET http://localhost:5000/api/stats \
  -H "Authorization: Bearer $TOKEN"
```

### 9. Check Gateway Balance
```bash
curl -X GET http://localhost:5000/api/gateway/balance \
  -H "Authorization: Bearer $TOKEN"
```

### 10. Health Check (No Auth Required)
```bash
curl -X GET http://localhost:5000/api/health
```

## Python Examples

See `example_usage.py` for a complete Python client implementation.

### Quick Python Example
```python
import requests

# Login
response = requests.post(
    "http://localhost:5000/api/auth/login",
    json={"username": "admin", "password": "admin123"}
)
token = response.json()["access_token"]

# Get contacts
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:5000/api/contacts",
    headers=headers
)
contacts = response.json()["contacts"]

# Send SMS
response = requests.post(
    "http://localhost:5000/api/sms/send",
    headers=headers,
    json={
        "to": "+1234567890",
        "content": "Hello from Python!"
    }
)
result = response.json()
```

## JavaScript/Node.js Example

```javascript
const axios = require('axios');

const API_URL = 'http://localhost:5000/api';

async function main() {
  // Login
  const loginResponse = await axios.post(`${API_URL}/auth/login`, {
    username: 'admin',
    password: 'admin123'
  });
  const token = loginResponse.data.access_token;
  
  const headers = {
    Authorization: `Bearer ${token}`
  };
  
  // Create contact
  await axios.post(`${API_URL}/contacts`, {
    name: 'Jane Doe',
    phone: '+1234567890',
    priority: 'high',
    relationship: 'parent'
  }, { headers });
  
  // Get contacts
  const contactsResponse = await axios.get(`${API_URL}/contacts`, { headers });
  console.log('Contacts:', contactsResponse.data.contacts);
  
  // Send SMS
  const smsResponse = await axios.post(`${API_URL}/sms/send`, {
    to: '+1234567890',
    content: 'Hello from JavaScript!'
  }, { headers });
  console.log('SMS sent:', smsResponse.data);
}

main().catch(console.error);
```

## Response Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid authentication
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource already exists (e.g., duplicate phone)
- `500 Internal Server Error` - Server error

## Rate Limiting

Currently, no rate limiting is implemented. For production use, consider implementing rate limiting using Flask-Limiter or similar middleware.

## CORS

CORS is enabled for all origins in development. For production, configure specific allowed origins in the Flask-CORS settings.
