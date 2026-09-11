# Copernicus

Web-based application for managing HPC projects and users at the supercomputer
center of Aix-Marseille University.

## Overview

Copernicus manages the lifecycle of HPC projects — from registration requests
through visa approval, project creation, user management, resource allocation
(renewal/extension/transformation), activity reporting, and expiration.

## Prerequisites

- Python 3.12+
- PostgreSQL 14+
- SSH access to a SLURM cluster (for remote operations)

## Installation

```bash
# Clone the repository
git clone <repo-url> copernicus
cd copernicus

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Configuration files are stored in the `instance/` directory:

| File              | Purpose                        |
|-------------------|--------------------------------|
| `copernicus.cfg`  | Main Flask application config  |
| `project.cfg`     | Project type definitions       |
| `mail.cfg`        | SMTP and email templates       |

### Environment / Config Variables

| Key                        | Description                              |
|----------------------------|------------------------------------------|
| `SQLALCHEMY_DATABASE_URI`  | PostgreSQL connection string             |
| `SECRET_KEY`               | Flask session secret                     |
| `SSH_SERVER` / `SSH_KEY`   | Remote SSH connection for SLURM commands |
| `LOGIN_SERVER`             | SSH server for password authentication   |
| `MAIL_SEND`                | Enable/disable email sending             |
| `CACHE_TYPE`               | Flask-Caching backend (default: simple)  |

## PostgreSQL Setup

```sql
CREATE DATABASE copernicus;
CREATE USER copernicus WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE copernicus TO copernicus;
```

Configure the connection string in `instance/copernicus.cfg` for example:

```ini
SQLALCHEMY_DATABASE_URI = postgresql://copernicus:your_password@localhost:5432/copernicus
```

## Running the Application

```bash
python run.py
```