# 🚀 Lyftr: FastAPI Messaging Webhook & Analytics Service

A **production-ready backend service** to ingest message webhooks, query messages with filters, and expose advanced analytics/statistics. Built with **FastAPI** and **SQLAlchemy**.

---

## ✨ Features

- 🔒 **Secure webhook endpoint** with HMAC signature validation  
- ✅ **Idempotent inserts** to prevent duplicate message IDs  
- 📄 **Powerful message query API**: pagination, text search, sender/receiver/time filters  
- 📊 **Analytics & statistics endpoint**: total messages, top senders, time ranges  
- 📈 **Prometheus-compatible metrics** for monitoring  
- 📝 **Structured JSON logging**  
- 🗄️ **SQLite by default**, configurable for other databases  

---

## ⚡ Quickstart

### 1. Clone the repository

2. Configure Environment

Create a .env file in the project root:

DATABASE_URL=sqlite:///./data/app.db      # SQLAlchemy DB URI
WEBHOOK_SECRET=your_webhook_secret_key   # HMAC secret key
LOG_LEVEL=INFO                            # Optional: DEBUG, INFO, WARN

3. Build & Run with Docker

Make sure Docker Desktop is running. Then run:

make up


This will build and start the service in a container

App will be available at: http://127.0.0.1:8000

Endpoints
1. Webhook Ingest

POST /webhook

Headers:
X-Signature: <hmac-sha256>

Body (JSON):

{
  "message_id": "string",
  "from": "+1234567890",
  "to": "+1987654321",
  "ts": "YYYY-MM-DDTHH:MM:SSZ",
  "text": "Optional message"
}

2. Message Query

GET /messages

Query Parameters:

limit (int)

offset (int)

from (string, phone number)

to (string, phone number)

since (ISO datetime)

q (string, text search)

3. Stats

GET /stats
Returns: total messages, unique senders, top 10 senders, message time range.

4. Metrics

GET /metrics
Prometheus-compatible metrics.

5. Health Checks

GET /health/live

GET /health/ready

Project Structure
.
├── app/
│   ├── main.py          # FastAPI app & endpoints
│   ├── models.py        # SQLAlchemy & Pydantic models
│   ├── database.py      # DB init & session management
│   ├── config.py        # Settings & env loader
│   ├── metrics.py       # Metrics recording
│   ├── logging_utils.py # JSON logging + middleware
│   ├── utils.py         # HMAC & helper functions
│   └── ...
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Docker Compose setup
├── Dockerfile           # Containerize the app
├── Makefile             # Build/run commands (`make up`)
└── README.md

Makefile Commands
Command	Description
make up	Build & start the app via Docker
make down	Stop & remove containers
make logs	Tail container logs

Tip: Ensure Docker Desktop is running before executing make up.
