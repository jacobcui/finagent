# AWS Deployment Guide

## Prerequisites
- An AWS EC2 instance (Ubuntu 22.04 LTS recommended).
- Security Group allowing inbound traffic on ports:
  - 22 (SSH)
  - 5000 (Backend API)
  - 8501 (Frontend UI)

## Installation Steps

1. **SSH into your instance**:
   ```bash
   ssh -i key.pem ubuntu@your-ec2-ip
   ```

2. **Clone the repository**:
   ```bash
   git clone <your-repo-url> finagent
   cd finagent
   ```

3. **Run the Setup Script**:
   This script will install dependencies, set up the virtual environment, initialize the database, and configure systemd services.
   ```bash
   chmod +x scripts/setup_aws.sh
   ./scripts/setup_aws.sh
   ```

4. **Start Services**:
   ```bash
   sudo systemctl start finagent-backend
   sudo systemctl start finagent-frontend
   ```

5. **Verify Status**:
   ```bash
   sudo systemctl status finagent-backend
   sudo systemctl status finagent-frontend
   ```

6. **Access the Application**:
   - Frontend: `http://your-ec2-ip:8501`
   - Backend API: `http://your-ec2-ip:5000`

## Troubleshooting

- **Logs**:
  - Backend: `journalctl -u finagent-backend -f`
  - Frontend: `journalctl -u finagent-frontend -f`

- **Database**:
  The default setup uses SQLite (`finagent.db`). For production, consider switching to PostgreSQL by setting the `DATABASE_URL` environment variable in the service files.
