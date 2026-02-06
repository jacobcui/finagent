#!/bin/bash

# Exit on error
set -e

echo "Starting FinAgent Setup on AWS..."

# 1. System Updates
echo "Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install System Dependencies
echo "Installing system dependencies..."
# - python3-venv, pip: Python basics
# - libpango-1.0-0, libpangoft2-1.0-0: Required for WeasyPrint
# - libpq-dev: Required for psycopg2 (if using Postgres)
# - nginx: For reverse proxy (optional but recommended)
sudo apt-get install -y python3-pip python3-venv libpango-1.0-0 libpangoft2-1.0-0 libpq-dev nginx git

# 3. Project Setup
PROJECT_DIR="/home/ubuntu/finagent"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Directory $PROJECT_DIR does not exist. Assuming we are already inside the repo or cloning..."
    # If script is run from within the repo, use current dir
    PROJECT_DIR=$(pwd)
fi

cd "$PROJECT_DIR"
echo "Working directory: $PROJECT_DIR"

# 4. Python Environment
echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing Python requirements..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Database Initialization
echo "Initializing Database..."
export PYTHONPATH=$PROJECT_DIR
# Run the init_db module
python3 -m src.framework.init_db

# 6. Setup Systemd Services
echo "Setting up Systemd services..."

# Backend Service
sudo cp scripts/finagent-backend.service /etc/systemd/system/
sudo sed -i "s|/path/to/finagent|$PROJECT_DIR|g" /etc/systemd/system/finagent-backend.service

# Frontend Service
sudo cp scripts/finagent-frontend.service /etc/systemd/system/
sudo sed -i "s|/path/to/finagent|$PROJECT_DIR|g" /etc/systemd/system/finagent-frontend.service

# Reload Systemd
sudo systemctl daemon-reload
sudo systemctl enable finagent-backend
sudo systemctl enable finagent-frontend

echo "Setup Complete!"
echo "To start services, run:"
echo "sudo systemctl start finagent-backend"
echo "sudo systemctl start finagent-frontend"
