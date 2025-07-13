#!/bin/bash

# Production start script for FastAPI application
echo "Installing dependencies with binary-only flags..."
export CARGO_HOME=/tmp/cargo
export RUSTUP_HOME=/tmp/rustup
pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the FastAPI application with gunicorn
echo "Starting FastAPI application..."
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT 