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

### Step 3: Get API Keys

#### **Google Gemini API Key**

1. **Visit Google AI Studio:**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account

2. **Create API Key:**
   - Click "Create API Key"
   - Select a Google Cloud project (or create a new one)
   - Copy the generated API key

3. **Enable API (if needed):**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to "APIs & Services" > "Library"
   - Search for "Generative Language API"
   - Enable the API for your project

#### 💳 **Stripe API Keys**

1. **Create Stripe Account:**
   - Go to [Stripe Dashboard](https://dashboard.stripe.com/)
   - Sign up for a free account
   - Complete account verification

2. **Get API Keys:**
   - In the Stripe Dashboard, go to "Developers" > "API Keys"
   - Copy the **Publishable Key** and **Secret Key** from the "Test Data" section

3. **Create Price ID:**
   - Go to "Products" > "Create Product"
   - Add a product (e.g., "Pro Subscription")
   - Set pricing (e.g, $0/month) (recommenede for easier webhook flow)
   - Copy the **Price ID** from the pricing section

4. **Setup Webhook:**
   - Go to "Developers" > "Webhooks"
   - Click "Add endpoint"
   - Set up ngrok for localhost 8000
   ```bash
    ngrok http 8000
    ```
   - Add endpoint URL: `https://{ngrok-url}/api/v1/webhooks/stripe`
   - Select events: `invoice.payment_succeeded`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Copy the **Webhook Secret** from the webhook details

### Step 4: Environment Variables

Create a `.env` file in the root directory and copy the contents of .env.example


### Step 5: Database Migrations

```bash
alembic revision --autogenerate -m "Initial migration"

alembic upgrade head
```

### Step 6: Run the Application

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
5. **API Keys**: Follow the detailed instructions above to get your Google Gemini and Stripe API keys


### Health Check

Visit `http://localhost:8000/health` to check if the application is running properly.
