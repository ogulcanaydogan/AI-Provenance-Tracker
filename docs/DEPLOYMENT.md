# Deployment Guide

## Frontend - Vercel

### Option 1: Vercel Dashboard (Recommended)

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click "New Project"
3. Import `ogulcanaydogan/ai-provenance-tracker`
4. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Next.js
   - **Environment Variables**:
     - `NEXT_PUBLIC_API_URL`: Your Railway backend URL (e.g., `https://ai-provenance-api.up.railway.app`)
5. Click "Deploy"

### Option 2: Vercel CLI

```bash
npm i -g vercel
cd frontend
vercel --prod
```

## Backend - Railway

### Option 1: Railway Dashboard (Recommended)

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select `ogulcanaydogan/ai-provenance-tracker`
4. Configure:
   - **Root Directory**: `backend`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `DEBUG`: `false`
   - `ENVIRONMENT`: `production`
   - `ALLOWED_ORIGINS`: `["https://your-vercel-url.vercel.app"]`
6. Generate a domain and deploy

### Option 2: Railway CLI

```bash
npm i -g @railway/cli
railway login
cd backend
railway init
railway up
```

## Alternative: Fly.io for Backend

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and deploy
cd backend
fly launch
fly deploy
```

## Environment Variables

### Frontend (.env.production)
```
NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
```

### Backend
```
DEBUG=false
ENVIRONMENT=production
ALLOWED_ORIGINS=["https://your-frontend.vercel.app"]
DATABASE_URL=postgresql://...  # Optional
REDIS_URL=redis://...          # Optional
```

## Post-Deployment Checklist

- [ ] Frontend loads correctly
- [ ] API health check responds: `GET /health`
- [ ] Text detection works: `POST /api/v1/detect/text`
- [ ] Image detection works: `POST /api/v1/detect/image`
- [ ] CORS configured correctly
- [ ] SSL certificates active

## Custom Domain (Optional)

### Vercel
1. Project Settings → Domains
2. Add your domain
3. Update DNS records

### Railway
1. Project Settings → Domains
2. Add custom domain
3. Update DNS records

## Monitoring

- Vercel Analytics: Built-in
- Railway Logs: Dashboard → Deployments → Logs
- API Docs: `https://your-backend/docs`
