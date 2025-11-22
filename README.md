# SMS Hub - Self-Hosted Family SMS Gateway

A self-hosted SMS hub built with Python/Flask and MySQL for managing family communications via GSM modem. Features AI-powered message classification, contact management, and JWT-secured API endpoints.

## 🚀 Features

### Core Functionality
- **Contact Management**: Store and manage family/friend contacts with priority levels and relationships
- **SMS Gateway Integration**: Send/receive SMS via Jasmin SMS Gateway with GSM modem support
- **AI Message Classification**: Automatic critical/stable message classification using OpenAI GPT-4 or Google Gemini
- **JWT Authentication**: Secure API endpoints with JSON Web Token authentication
- **Message History**: Track all sent/received messages with status and classification
- **RESTful API**: Complete REST API for all operations

### Technical Stack
- **Backend**: Python 3.10+, Flask 3.0
- **Database**: MySQL 8.0
- **SMS Gateway**: Jasmin SMS Gateway
- **AI/ML**: OpenAI GPT-4 or Google Gemini
- **Authentication**: JWT (Flask-JWT-Extended)
- **Deployment**: Docker & Docker Compose

## 📋 Requirements

- Python 3.10 or higher
- MySQL 8.0 or higher
- Docker & Docker Compose (recommended for deployment)
- GSM modem (for actual SMS sending)
- OpenAI API key or Google Gemini API key (for message classification)

## 🛠️ Installation

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**
```bash
git clone https://github.com/spwotton/sms.git
cd sms
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
nano .env
```

3. **Start the services**
```bash
docker-compose up -d
```

The API will be available at `http://localhost:5000`

### Option 2: Manual Installation

1. **Clone and setup**
```bash
git clone https://github.com/spwotton/sms.git
cd sms
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure MySQL**
```bash
# Create database
mysql -u root -p
CREATE DATABASE sms_hub;
CREATE USER 'sms_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON sms_hub.* TO 'sms_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# Import schema
mysql -u sms_user -p sms_hub < init.sql
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run the application**
```bash
python app.py
```

## 🔧 Configuration

Edit `.env` file with your settings:

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=sms_user
DB_PASSWORD=your_password
DB_NAME=sms_hub

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-change-in-production

# Jasmin SMS Gateway
JASMIN_API_URL=http://localhost:8080
JASMIN_API_USERNAME=admin
JASMIN_API_PASSWORD=password

# AI Provider (openai or gemini)
AI_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4

# OR use Gemini
# AI_PROVIDER=gemini
# GEMINI_API_KEY=your-gemini-api-key
# GEMINI_MODEL=gemini-pro
```

## 📚 API Documentation

### Authentication

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}

Response: 200 OK
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer"
}
```

**Note**: Use the access token in the Authorization header for all subsequent requests:
```
Authorization: Bearer <access_token>
```

### Contact Management

#### Get All Contacts
```http
GET /api/contacts
Authorization: Bearer <token>

Response: 200 OK
{
  "contacts": [
    {
      "id": 1,
      "name": "John Doe",
      "phone": "+1234567890",
      "priority": "high",
      "relationship": "parent",
      "created_at": "2024-01-01T12:00:00",
      "updated_at": "2024-01-01T12:00:00"
    }
  ]
}
```

#### Get Single Contact
```http
GET /api/contacts/<contact_id>
Authorization: Bearer <token>
```

#### Create Contact
```http
POST /api/contacts
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "John Doe",
  "phone": "+1234567890",
  "priority": "high",
  "relationship": "parent"
}

Response: 201 Created
```

**Priority Levels**: `low`, `medium`, `high`, `critical`  
**Relationship Types**: `parent`, `child`, `sibling`, `spouse`, `friend`, `extended_family`, `other`

#### Update Contact
```http
PUT /api/contacts/<contact_id>
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "John Doe Updated",
  "priority": "critical"
}
```

#### Delete Contact
```http
DELETE /api/contacts/<contact_id>
Authorization: Bearer <token>
```

### SMS Operations

#### Send SMS
```http
POST /api/sms/send
Authorization: Bearer <token>
Content-Type: application/json

{
  "to": "+1234567890",
  "content": "Hello! This is a test message.",
  "from": "+0987654321"  // optional
}

Response: 200 OK
{
  "message": "SMS sent successfully",
  "result": {
    "status": "sent",
    "message_id": "abc123"
  },
  "classification": "stable",
  "message_id": 1
}
```

The message will be automatically classified as either:
- **critical**: Emergency, urgent, safety concerns
- **stable**: General conversation, routine updates

#### Get Messages
```http
GET /api/messages?limit=50&classification=critical
Authorization: Bearer <token>

Query Parameters:
- contact_id: Filter by contact ID
- direction: inbound or outbound
- classification: critical or stable
- limit: Number of messages (default: 100)

Response: 200 OK
{
  "messages": [...],
  "count": 50
}
```

#### Get Single Message
```http
GET /api/messages/<message_id>
Authorization: Bearer <token>
```

### Gateway Operations

#### Check Balance
```http
GET /api/gateway/balance
Authorization: Bearer <token>

Response: 200 OK
{
  "status": "success",
  "balance": "100"
}
```

#### Check Message Status
```http
GET /api/gateway/status/<message_id>
Authorization: Bearer <token>
```

### Statistics

#### Get System Stats
```http
GET /api/stats
Authorization: Bearer <token>

Response: 200 OK
{
  "total_contacts": 25,
  "total_messages": 150,
  "critical_messages": 10,
  "stable_messages": 140
}
```

### Health Check

#### Check API Health
```http
GET /api/health

Response: 200 OK
{
  "status": "healthy",
  "service": "SMS Hub API"
}
```

## 🔌 Jasmin SMS Gateway Setup

1. **Install Jasmin** (if not using Docker)
```bash
pip install jasmin
```

2. **Configure Jasmin with your GSM modem**
   - Follow Jasmin documentation for modem setup
   - Configure SMPP connection
   - Set up REST API access

3. **Update environment variables**
```env
JASMIN_API_URL=http://localhost:8080
JASMIN_API_USERNAME=your_username
JASMIN_API_PASSWORD=your_password
```

## 🤖 AI Message Classification

The system uses AI to automatically classify messages as either:

- **Critical**: Emergency situations, urgent help requests, safety concerns
- **Stable**: General conversation, routine updates, social chat

### Supported AI Providers

1. **OpenAI GPT-4** (recommended)
   - More accurate classification
   - Better understanding of context
   - Requires OpenAI API key

2. **Google Gemini**
   - Free tier available
   - Good performance
   - Requires Google AI API key

Configure in `.env`:
```env
AI_PROVIDER=openai  # or gemini
OPENAI_API_KEY=your-key
```

## 🧪 Testing

Run tests with pytest:
```bash
pytest
```

## 🔒 Security

- All API endpoints require JWT authentication
- Change default credentials in production
- Use strong secret keys
- Keep API keys secure
- Use HTTPS in production
- Implement rate limiting for production use

## 📦 Database Schema

### Contacts Table
```sql
CREATE TABLE contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    priority ENUM('low', 'medium', 'high', 'critical'),
    relationship ENUM('parent', 'child', 'sibling', 'spouse', 'friend', 'extended_family', 'other'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Messages Table
```sql
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    contact_id INT,
    phone VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    direction ENUM('inbound', 'outbound'),
    status ENUM('pending', 'sent', 'delivered', 'failed'),
    classification ENUM('stable', 'critical'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);
```

## 🚀 Production Deployment

### Docker Deployment
```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Manual Production Setup
1. Use gunicorn for production WSGI server
2. Set up nginx as reverse proxy
3. Configure SSL/TLS certificates
4. Enable firewall rules
5. Set up monitoring and logging
6. Configure automatic backups for MySQL

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

For issues, questions, or contributions, please open an issue on GitHub.

## 📞 Contact

Project Link: [https://github.com/spwotton/sms](https://github.com/spwotton/sms)
