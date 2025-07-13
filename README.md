# Gemini-Style Backend System

A comprehensive backend system that enables user-specific chatrooms, OTP-based authentication, AI-powered conversations using Google Gemini API, and subscription handling via Stripe.

## 🏗️ **Architecture Overview**

```
├── app/
│   ├── api/v1/           # API endpoints
│   │   ├── endpoints/    # Route handlers
│   │   └── api.py       # Main router
│   ├── core/            # Core configuration
│   │   ├── config.py    # Settings & environment
│   │   └── database.py  # Database connection
│   ├── models/          # Database models
│   │   ├── user.py      # User model
│   │   ├── chatroom.py  # Chatroom model
│   │   ├── message.py   # Message model
│   │   ├── subscription.py # Subscription model
│   │   ├── otp.py       # OTP verification
│   │   └── daily_usage.py # Usage tracking
│   ├── deps.py          # Dependencies
│   └── main.py          # FastAPI application
├── alembic/             # Database migrations
├── requirement.txt      # Python dependencies
└── .env                 # Environment variables
```

## **Getting Started**

### Prerequisites

1. **Python 3.8+**
2. **PostgreSQL 12+**
3. **Redis 6+**
4. **Google Gemini API Key**
5. **Stripe Account (Sandbox)**

### Step 1: Environment Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd gemini-chatroom
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirement.txt
   ```

### Step 2: Database Setup

1. **Create PostgreSQL database:**

   Use PgAdmin 4 for easier setup.
   Otherwise - make sure postgresql is intsall.

   ```sql
   CREATE DATABASE chatroom_db;
   CREATE USER postgres WITH PASSWORD 'postgres';
   GRANT ALL PRIVILEGES ON DATABASE chatroom_db TO postgres;
   ```

2. **Start Redis server:**

   ### Using Docker to run Redis (more easier)

   ```bash
   docker run --name redis-server -p 6379:6379 -d redis:6
   ```

   To stop and remove the container:

   ```bash
   docker stop redis-server
   docker rm redis-server
   ```

   ```bash
   redis-server
   ```

### Step 3: Environment Variables

Create a `.env` file in the root directory and copy the contents of .env.example


### Step 4: Database Migrations

```bash
alembic revision --autogenerate -m "Initial migration"

alembic upgrade head
```

### Step 5: Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# or using Python directly
python app/main.py
```


## 🧪 **Testing**

Access the API documentation and enpoints at:
- **Swagger UI**: `http://localhost:8000/docs`

## 📝 **Notes**

1. **Database Connection**: Make sure PostgreSQL is running before starting the application
2. **Redis**: Required for caching and message queuing
3. **Environment Variables**: All sensitive keys should be set in `.env`
4. **Migrations**: Always run migrations when database schema changes
5. **API Keys**: Get your Google Gemini API key from Google AI Studio


### Health Check

Visit `http://localhost:8000/health` to check if the application is running properly.
