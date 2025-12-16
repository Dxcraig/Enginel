# Railway Deployment Quick Reference

## Service Configuration

### App Service (Web)
- **Source**: GitHub repo
- **Dockerfile**: `Dockerfile`
- **Start Command**: *(leave empty - uses entrypoint.sh)*
- **Environment Variables**: See below
- **Public Domain**: Generate after deployment

### Worker Service (Celery)
- **Source**: Same GitHub repo
- **Dockerfile**: `Dockerfile`
- **Start Command**: `celery -A enginel worker -l info --concurrency=4`
- **Environment Variables**: Copy from App Service

### Cron Service (Celery Beat)
- **Source**: Same GitHub repo
- **Dockerfile**: `Dockerfile`
- **Start Command**: `celery -A enginel beat -l info`
- **Environment Variables**: Copy from App Service

### PostgreSQL Database
- **Type**: Add PostgreSQL from Railway
- **Auto-variables**: PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE

### Redis Database
- **Type**: Add Redis from Railway
- **Auto-variables**: REDIS_URL, REDISHOST, REDISPORT, REDISPASSWORD

## Required Environment Variables

```bash
# App Service Variables
SECRET_KEY=<generate-secure-key>
DEBUG=False
ALLOWED_HOSTS=.railway.app

# Database (reference PostgreSQL)
PGDATABASE=${{Postgres.PGDATABASE}}
PGUSER=${{Postgres.PGUSER}}
PGPASSWORD=${{Postgres.PGPASSWORD}}
PGHOST=${{Postgres.PGHOST}}
PGPORT=${{Postgres.PGPORT}}

# Redis (reference Redis)
REDIS_URL=${{Redis.REDIS_URL}}

# AWS S3 (optional)
USE_S3=True
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_STORAGE_BUCKET_NAME=<bucket-name>
AWS_S3_REGION_NAME=us-east-1

# Security
SECURE_SSL_REDIRECT=True
CSRF_TRUSTED_ORIGINS=https://<your-domain>.railway.app
```

## Deployment Steps

1. **Push to GitHub**
2. **Create Railway project** → Deploy from GitHub
3. **Add PostgreSQL** → Database → PostgreSQL
4. **Add Redis** → Database → Redis
5. **Configure App Service** → Add environment variables
6. **Create Worker Service** → Empty service + start command
7. **Create Cron Service** → Empty service + start command
8. **Generate domain** → App Service → Settings → Networking
9. **Create superuser** → `railway run python manage.py createsuperuser`

## Common Commands

```bash
# Link to Railway project
railway link

# Create superuser
railway run python manage.py createsuperuser

# View logs
railway logs
railway logs --service worker

# Run migrations (automatic on deploy)
railway run python manage.py migrate

# Open project dashboard
railway open
```

## Troubleshooting

**Container fails to start**
- Check Dockerfile builds locally: `docker build -t enginel .`
- Verify environment variables are set
- Check logs: `railway logs`

**Database connection error**
- Verify PostgreSQL service is running
- Check database variables reference correctly: `${{Postgres.PGHOST}}`
- Test connection in shell

**Worker not processing tasks**
- Check Redis connection
- Verify REDIS_URL is set
- Check worker logs: `railway logs --service worker`

**Static files not loading**
- Automatic via entrypoint.sh on deploy
- WhiteNoise serves static files
- Check logs for collectstatic output

## Architecture

```
Internet
   ↓
App Service (Port 8000) ← Public Domain
   ↓
   ├→ PostgreSQL (internal)
   ├→ Redis (internal)
   │
   ├→ Worker Service → Redis
   └→ Cron Service → Redis
```

## Cost Estimate

- App Service: ~$5-10/month
- Worker Service: ~$3-5/month  
- Cron Service: ~$2-3/month
- PostgreSQL: ~$2-5/month
- Redis: ~$1-2/month
**Total: ~$13-25/month**

## Important Notes

- ✅ Migrations run automatically on deploy
- ✅ Static files collected automatically
- ✅ Gunicorn used in production (Railway)
- ✅ Development server used locally (Docker Compose)
- ⚠️ Worker and Cron need custom start commands
- ⚠️ All services must have same environment variables
- ⚠️ Generate domain before updating CSRF_TRUSTED_ORIGINS
