#!/bin/bash

# Production start script for FastAPI application
echo "Installing dependencies with binary-only flags..."
pip install --upgrade pip setuptools wheel
pip install --only-binary=:all: -r requirements.txt

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the FastAPI application with gunicorn
echo "Starting FastAPI application..."
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker