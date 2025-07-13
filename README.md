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

## 🚀 **Getting Started**

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
   cd kuvata-assignment
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
   ```sql
   CREATE DATABASE chatroom_db;
   CREATE USER postgres WITH PASSWORD 'postgres';
   GRANT ALL PRIVILEGES ON DATABASE chatroom_db TO postgres;
   ```

2. **Start Redis server:**
   ```bash
   redis-server
   ```

### Step 3: Environment Variables

Create a `.env` file in the root directory:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chatroom_db
DB_USER=postgres
DB_PASSWORD=postgres

# Redis Configuration
REDIS_URL=redis://localhost:6379

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Stripe Configuration (Sandbox)
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_PRICE_ID_PRO=price_your_price_id_here

# Google Gemini API Configuration
GOOGLE_API_KEY=your_google_api_key_here

# OTP Configuration
OTP_EXPIRATION_MINUTES=5

# Rate Limiting
BASIC_TIER_DAILY_LIMIT=5

# Caching
CACHE_TTL_SECONDS=300

# Application Settings
APP_NAME=Gemini-Style Chatroom
DEBUG=True

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379
CELERY_RESULT_BACKEND=redis://localhost:6379
```

### Step 4: Database Migrations

```bash
# Generate migration (when database is running)
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### Step 5: Run the Application

```bash
# Development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python directly
python app/main.py
```

## 📊 **API Endpoints**

### Authentication
- `POST /api/v1/auth/signup` - Register new user
- `POST /api/v1/auth/send-otp` - Send OTP to mobile
- `POST /api/v1/auth/verify-otp` - Verify OTP & get JWT
- `POST /api/v1/auth/forgot-password` - Reset password
- `POST /api/v1/auth/change-password` - Change password

### User Management
- `GET /api/v1/user/me` - Get current user info

### Chatrooms
- `POST /api/v1/chatroom` - Create new chatroom
- `GET /api/v1/chatroom` - List user chatrooms (cached)
- `GET /api/v1/chatroom/{id}` - Get chatroom details
- `POST /api/v1/chatroom/{id}/message` - Send message & get AI response

### Subscriptions
- `POST /api/v1/subscription/pro` - Subscribe to Pro tier
- `GET /api/v1/subscription/status` - Get subscription status

### Webhooks
- `POST /api/v1/webhook/stripe` - Stripe webhook handler

## 🔧 **Development Status**

### ✅ **Phase 1: Foundation (COMPLETED)**
- [x] Project structure setup
- [x] Database models design
- [x] FastAPI application setup
- [x] Environment configuration
- [x] Database migrations setup

### 🔄 **Phase 2: Authentication (NEXT)**
- [ ] JWT token handling
- [ ] OTP generation & verification
- [ ] User registration & login
- [ ] Authentication middleware

### 🔄 **Phase 3: Core Features (UPCOMING)**
- [ ] Chatroom management
- [ ] Message system
- [ ] Google Gemini API integration
- [ ] Async queue system (Celery)

### 🔄 **Phase 4: Advanced Features (UPCOMING)**
- [ ] Stripe subscription integration
- [ ] Usage limits & rate limiting
- [ ] Redis caching
- [ ] Webhook handling

### 🔄 **Phase 5: Deployment (UPCOMING)**
- [ ] Docker configuration
- [ ] Environment setup
- [ ] Postman collection
- [ ] Documentation

## 🏛️ **Key Features**

### Authentication System
- **OTP-based login** with mobile number only
- **JWT tokens** for session management
- **Password reset** functionality

### Chatroom System
- **Multiple chatrooms** per user
- **AI-powered conversations** using Google Gemini
- **Message history** and status tracking
- **Async processing** with message queues

### Subscription Management
- **Basic tier** (Free): 5 messages/day
- **Pro tier** (Paid): Unlimited messages
- **Stripe integration** for payments
- **Webhook handling** for events

### Performance Optimizations
- **Redis caching** for chatroom listings
- **Query optimization** for better performance
- **Rate limiting** for Basic tier users

## 🧪 **Testing**

Access the API documentation at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📝 **Notes**

1. **Database Connection**: Make sure PostgreSQL is running before starting the application
2. **Redis**: Required for caching and message queuing
3. **Environment Variables**: All sensitive keys should be set in `.env`
4. **Migrations**: Always run migrations when database schema changes
5. **API Keys**: Get your Google Gemini API key from Google AI Studio

## 🔍 **Troubleshooting**

### Common Issues

1. **Database connection error**: Check if PostgreSQL is running and credentials are correct
2. **Redis connection error**: Ensure Redis server is running
3. **Import errors**: Make sure all dependencies are installed
4. **Migration errors**: Check database permissions and connection

### Health Check

Visit `http://localhost:8000/health` to check if the application is running properly.

---

**Next Steps**: We'll implement the authentication system (Phase 2) in the next iteration! 