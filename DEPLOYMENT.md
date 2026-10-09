# TravClan Agent Copilot - Deployment Guide

This guide covers deploying the TravClan Agent Copilot to GitHub and Vercel (frontend) with options for the backend.

## Architecture Overview

- **Frontend**: React + Vite (static SPA) → Deploy to Vercel
- **Backend**: FastAPI + PostgreSQL → Deploy to Railway/Render/Fly.io/Cloud Run
- **Database**: PostgreSQL (managed by hosting provider)

---

## 1. GitHub Repository Setup

### Initialize Git and Push to GitHub

```bash
# In the project root
git init
git add .
git commit -m "Initial commit: TravClan Agent Copilot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/travclan-agent-copilot.git
git push -u origin main
```

### Required GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|--------|-------------|
| `VERCEL_TOKEN` | Vercel access token (from Vercel account settings) |
| `VERCEL_ORG_ID` | Vercel organization ID |
| `VERCEL_PROJECT_ID` | Vercel project ID |
| `RAILWAY_TOKEN` | (Optional) Railway API token for backend deploy |
| `RAILWAY_SERVICE` | (Optional) Railway service name |

---

## 2. Frontend Deployment (Vercel)

### Option A: Automatic via GitHub Integration (Recommended)

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **Add New... → Project**
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`
5. Add Environment Variables:
   - `VITE_API_URL` = Your backend URL (e.g., `https://api.yourapp.com/api`)
   - `VITE_API_ROOT` = Your backend root (e.g., `https://api.yourapp.com`)
6. Click **Deploy**

### Option B: Manual CLI Deploy

```bash
# Install Vercel CLI
npm install -g vercel@latest

# Login
vercel login

# Deploy from frontend directory
cd frontend
vercel --prod
```

### Vercel Configuration

The `vercel.json` in the project root handles:
- SPA routing (fallback to index.html)
- Security headers
- Static asset caching
- API rewrites to your backend

**Important**: Update the `rewrites` section in `vercel.json` with your actual backend URL:

```json
"rewrites": [
  {
    "source": "/api/(.*)",
    "destination": "https://your-actual-backend-url.com/api/$1"
  },
  {
    "source": "/health",
    "destination": "https://your-actual-backend-url.com/health"
  }
]
```

---

## 3. Backend Deployment Options

The backend requires a PostgreSQL database. Choose one:

### Option A: Railway (Easiest for full-stack)

1. Go to [Railway](https://railway.app)
2. Create new project → **Deploy from GitHub repo**
3. Select your repo
4. Add PostgreSQL database: **New → Database → PostgreSQL**
5. Set environment variables:
   ```
   DATABASE_URL=postgresql+psycopg2://user:pass@host:port/db
   EMBEDDING_BACKEND=auto
   EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   LLM_PROVIDER=none
   REQUIRE_AUTH=false
   API_KEY=your-secure-key
   DATA_SEED=42
   ```
6. Set **Root Directory** to `.` (project root)
7. Set **Build Command**: (empty - uses Dockerfile)
8. Set **Start Command**: (empty - uses Dockerfile CMD)

### Option B: Render

1. Go to [Render](https://render.com)
2. **New → Web Service** → Connect GitHub repo
3. Configure:
   - **Root Directory**: `.`
   - **Build Command**: (empty - uses Dockerfile)
   - **Start Command**: (empty - uses Dockerfile CMD)
4. Add **PostgreSQL** database
5. Set environment variables (same as Railway)

### Option C: Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and launch
flyctl auth login
flyctl launch --name travclan-copilot --region iad --dockerfile Dockerfile

# Create PostgreSQL
flyctl postgres create --name travclan-db

# Set secrets
flyctl secrets set DATABASE_URL=... EMBEDDING_BACKEND=auto LLM_PROVIDER=none

# Deploy
flyctl deploy
```

### Option D: Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/travclan-backend

# Deploy
gcloud run deploy travclan-backend \
  --image gcr.io/PROJECT_ID/travclan-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=...,EMBEDDING_BACKEND=auto
```

---

## 4. Database Setup

The backend auto-seeds synthetic data on first startup if the database is empty.

For production, you may want to:
1. Run migrations (if using Alembic)
2. Seed with real data
3. Set up backups

```bash
# Manual seed (if needed)
docker exec -it <container> python -m scripts.seed_database
```

---

## 5. Environment Variables Reference

### Backend (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/processed/copilot.db` | PostgreSQL connection string |
| `EMBEDDING_BACKEND` | `auto` | `auto`, `st`, or `hash` |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `LLM_PROVIDER` | `none` | `none`, `openai`, `anthropic`, `gemini` |
| `LLM_API_KEY` | `` | API key for LLM provider |
| `REQUIRE_AUTH` | `false` | Enable API key auth |
| `API_KEY` | `change-me` | API key if auth enabled |
| `DATA_SEED` | `42` | Random seed for synthetic data |

### Frontend (Vercel Environment Variables)

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API base URL (e.g., `https://api.yourapp.com/api`) |
| `VITE_API_ROOT` | Backend root URL (e.g., `https://api.yourapp.com`) |

---

## 6. Local Development

### Using Docker Compose (Full Stack)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Manual (Without Docker)

**Backend:**
```bash
cd backend
pip install -r ../requirements.txt
# Create .env with DATABASE_URL=sqlite:///./data/processed/copilot.db
uvicorn app.main:app --app-dir backend --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## 7. CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push:

1. **Backend Tests** - Runs pytest
2. **Frontend Build & Lint** - Runs oxlint and Vite build
3. **Docker Build Test** - Verifies Docker images build
4. **Deploy to Vercel** - On push to main (frontend)
5. **Deploy Backend** - On push to main (configure your provider)

---

## 8. Custom Domain Setup

### Vercel (Frontend)
1. Go to Project Settings → Domains
2. Add your domain (e.g., `app.yourdomain.com`)
3. Configure DNS as instructed

### Backend (Railway/Render/Fly.io)
1. Add custom domain in provider dashboard
2. Update `VITE_API_URL` and `VITE_API_ROOT` in Vercel
3. Update `vercel.json` rewrites with new backend URL
4. Redeploy frontend

---

## 9. Monitoring & Health Checks

- **Backend Health**: `GET /health` → Returns `{ "status": "ok", ... }`
- **Frontend Health**: `GET /health` (nginx) → Returns `healthy`

Set up uptime monitoring (UptimeRobot, Pingdom, etc.) on both endpoints.

---

## 10. Troubleshooting

### Frontend can't connect to backend
- Check `VITE_API_URL` in Vercel environment variables
- Check `vercel.json` rewrites match your backend URL
- Verify CORS in backend (`allow_origins=["*"]` in main.py)

### Backend database connection failed
- Verify `DATABASE_URL` format: `postgresql+psycopg2://user:pass@host:port/db`
- Check database allows connections from your hosting provider's IPs
- Ensure database exists and user has permissions

### Build failures
- Check Node.js version (requires 18+)
- Check Python version (requires 3.11+)
- Clear caches: `docker builder prune`, `npm cache clean --force`

---

## 11. Cost Optimization

- **Vercel**: Free tier includes 100GB bandwidth/month
- **Railway**: $5/month hobby plan includes PostgreSQL
- **Render**: Free tier with limitations (spins down after inactivity)
- **Fly.io**: Pay for what you use, ~$5-10/month for small apps

---

## Support

For issues, check:
1. GitHub Actions logs
2. Vercel deployment logs
3. Backend provider logs
4. Browser console for frontend errors