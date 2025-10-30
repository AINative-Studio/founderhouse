# Quick Start Guide - AI Chief of Staff Backend

Get the FastAPI backend running in 5 minutes.

## Prerequisites Checklist

- [ ] Python 3.11+ installed
- [ ] Supabase account created
- [ ] Git installed

## Step-by-Step Setup

### 1. Install Dependencies (2 minutes)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment (1 minute)

```bash
cp .env.example .env
```

Edit `.env` and set these **required** values:

```bash
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-anon-key-here"
SECRET_KEY="generate-with-openssl-rand-hex-32"
```

To generate a secure secret key:
```bash
openssl rand -hex 32
```

### 3. Set Up Database (1 minute)

In Supabase SQL Editor, run:

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS ops;
CREATE SCHEMA IF NOT EXISTS comms;
CREATE SCHEMA IF NOT EXISTS meetings;
CREATE SCHEMA IF NOT EXISTS media;
CREATE SCHEMA IF NOT EXISTS work;
CREATE SCHEMA IF NOT EXISTS intel;
```

Then run the full schema from `/datamodel.md`.

### 4. Run the Server (1 minute)

```bash
uvicorn app.main:app --reload
```

Or simply:
```bash
make dev
```

### 5. Test It Works

Open http://localhost:8000/docs in your browser.

You should see the interactive API documentation!

## Quick Test Commands

### Check Health
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-30T12:00:00Z",
  "version": "0.1.0",
  "environment": "development",
  "database": {
    "status": "healthy",
    "database": "connected"
  }
}
```

### Check Version
```bash
curl http://localhost:8000/version
```

## Common Issues

### Issue: "Database health check failed"

**Solution**:
1. Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
2. Check your Supabase project is active
3. Test connection: `curl https://your-project.supabase.co/rest/v1/`

### Issue: "Module not found"

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Port 8000 already in use"

**Solution**:
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001

# Or kill the process using port 8000
lsof -ti:8000 | xargs kill -9  # Mac/Linux
```

## Next Steps

1. **Create a Workspace**
   - POST to `/api/v1/workspaces`
   - Requires authentication token

2. **Connect an Integration**
   - POST to `/api/v1/integrations/connect`
   - Start with Slack or Discord

3. **Explore the API**
   - Visit http://localhost:8000/docs
   - Try endpoints with the interactive UI

## Getting Authentication Token

For development, you can create a test token:

```python
# Python shell
from app.core.security import create_access_token
import uuid

token = create_access_token({
    "user_id": str(uuid.uuid4()),
    "workspace_id": str(uuid.uuid4()),
    "role": "owner"
})
print(token)
```

Use this token in API requests:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/workspaces
```

## Development Workflow

```bash
# Start dev server
make dev

# Run tests
make test

# Format code
make format

# Check code quality
make lint

# Clean temp files
make clean
```

## Docker Quick Start (Alternative)

```bash
# Build and run with Docker
docker-compose up --build

# Stop containers
docker-compose down
```

## Useful Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make dev` | Start development server |
| `make test` | Run test suite |
| `make docker-up` | Start with Docker |

## Support

- Full documentation: See `README.md`
- Issues: Check GitHub issues
- PRD: See `/prd.md`
- Sprint plan: See `/sprint-plan.md`

---

You're now ready to build! The FastAPI backend is running and ready for Sprint 1 development.
