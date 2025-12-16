# Railway Deployment Guide for Enginel

This guide walks you through deploying the Enginel Django application to Railway.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **Railway CLI** (optional): Install with `npm i -g @railway/cli` or `brew install railway`
3. **GitHub Repository**: Push your code to GitHub
4. **AWS S3 Account**: For file storage (optional but recommended)

## Architecture Overview

The Enginel application consists of **4 services**:

1. **App Service**: Django web application (handles HTTP requests)
2. **Worker Service**: Celery worker (processes background jobs)
3. **Cron Service**: Celery Beat (scheduled tasks)
4. **PostgreSQL Database**: Managed by Railway
5. **Redis Database**: Managed by Railway

## Deployment Steps

### Step 1: Create a New Railway Project

1. Go to [railway.app/new](https://railway.app/new)
2. Click "Deploy from GitHub repo"
3. Select your `Enginel` repository
4. Click "Deploy Now"

### Step 2: Add Database Services

#### Add PostgreSQL

1. In your Railway project, click "+ New"
2. Select "Database" → "Add PostgreSQL"
3. Railway will automatically provision and configure PostgreSQL
4. Environment variables will be auto-created:
   - `PGHOST`
   - `PGPORT`
   - `PGUSER`
   - `PGPASSWORD`
   - `PGDATABASE`
   - `DATABASE_URL`

#### Add Redis

1. In your Railway project, click "+ New"
2. Select "Database" → "Add Redis"
3. Railway will automatically provision and configure Redis
4. Environment variables will be auto-created:
   - `REDIS_URL`
   - `REDISHOST`
   - `REDISPORT`
   - `REDISPASSWORD`

### Step 3: Configure the App Service

1. Click on your app service
2. Go to the **Variables** tab
3. Add the following environment variables:

#### Required Variables

```bash
# Django
SECRET_KEY=<generate-a-secure-random-key>
DEBUG=False
ALLOWED_HOSTS=.railway.app

# Database (reference PostgreSQL service)
PGDATABASE=${{Postgres.PGDATABASE}}
PGUSER=${{Postgres.PGUSER}}
PGPASSWORD=${{Postgres.PGPASSWORD}}
PGHOST=${{Postgres.PGHOST}}
PGPORT=${{Postgres.PGPORT}}

# Redis (reference Redis service)
REDIS_URL=${{Redis.REDIS_URL}}

# AWS S3 (if using S3 storage)
USE_S3=True
AWS_ACCESS_KEY_ID=<your-aws-access-key>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-key>
AWS_STORAGE_BUCKET_NAME=<your-bucket-name>
AWS_S3_REGION_NAME=us-east-1
```

#### Optional Security Variables

```bash
# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_AGE=86400
PASSWORD_MIN_LENGTH=12

# CSRF & CORS
CSRF_TRUSTED_ORIGINS=https://<your-domain>.railway.app
CORS_ALLOWED_ORIGINS=https://<your-domain>.railway.app

# Rate Limiting
THROTTLE_ANON=100/hour
THROTTLE_USER=1000/hour

# IP Security
IP_WHITELIST=
IP_BLACKLIST=

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<your-email>
EMAIL_HOST_PASSWORD=<your-app-password>
DEFAULT_FROM_EMAIL=noreply@enginel.com
```

4. In the **Settings** tab:
   - Set **Start Command**: Leave empty (Railway will use Dockerfile)
   - Verify **Root Directory**: Should be `/`
   - Check **Dockerfile Path**: Should be `Dockerfile`

### Step 4: Create Worker Service

1. In your Railway project, click "+ New"
2. Select "Empty Service"
3. Name it "Worker Service"
4. Go to **Settings**:
   - Connect to the same GitHub repo
   - Set **Start Command**: `cd enginel && celery -A enginel worker -l info --concurrency=4`
5. Go to **Variables**:
   - Copy all variables from the App Service (or use reference variables)
   - Add the same database and Redis connection variables

### Step 5: Create Cron Service (Celery Beat)

1. In your Railway project, click "+ New"
2. Select "Empty Service"
3. Name it "Cron Service"
4. Go to **Settings**:
   - Connect to the same GitHub repo
   - Set **Start Command**: `cd enginel && celery -A enginel beat -l info`
5. Go to **Variables**:
   - Copy all variables from the App Service
   - Add the same database and Redis connection variables

### Step 6: Run Migrations

After the App Service is deployed:

1. Click on the App Service
2. Go to the **Deployments** tab
3. Click on the latest deployment
4. Open the **Shell** (or use Railway CLI)
5. Run migrations:

```bash
cd enginel
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Or use Railway CLI locally:

```bash
railway link
railway run python enginel/manage.py migrate
railway run python enginel/manage.py collectstatic --noinput
railway run python enginel/manage.py createsuperuser
```

### Step 7: Generate Public Domain

1. Click on the App Service
2. Go to **Settings** → **Networking**
3. Click **Generate Domain**
4. Railway will create a public URL: `https://<random>.railway.app`
5. Update your `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` with this domain

### Step 8: Verify Deployment

1. Visit your Railway URL
2. Check that the Django admin is accessible: `https://<your-app>.railway.app/admin/`
3. Verify logs in each service:
   - **App Service**: Should show Gunicorn running
   - **Worker Service**: Should show Celery worker ready
   - **Cron Service**: Should show Celery beat scheduler running

## Service Architecture

```
┌─────────────────┐
│   App Service   │ ← Public domain (HTTPS)
│   (Gunicorn)    │
└────────┬────────┘
         │
         ├─────────────┐
         │             │
    ┌────▼────┐   ┌───▼────┐
    │PostgreSQL│   │  Redis │
    └─────────┘   └────┬───┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
    ┌────▼────┐   ┌───▼────┐   ┌───▼────┐
    │  Worker │   │  Cron  │   │  Cache │
    │ Service │   │Service │   │        │
    └─────────┘   └────────┘   └────────┘
```

## Environment Variables Quick Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | - | Django secret key |
| `DEBUG` | ✅ | False | Debug mode |
| `ALLOWED_HOSTS` | ✅ | - | Allowed host domains |
| `PGDATABASE` | ✅ | - | PostgreSQL database name |
| `PGUSER` | ✅ | - | PostgreSQL username |
| `PGPASSWORD` | ✅ | - | PostgreSQL password |
| `PGHOST` | ✅ | - | PostgreSQL host |
| `PGPORT` | ✅ | 5432 | PostgreSQL port |
| `REDIS_URL` | ✅ | - | Redis connection URL |
| `USE_S3` | ❌ | False | Enable S3 storage |
| `AWS_ACCESS_KEY_ID` | ❌ | - | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | ❌ | - | AWS secret key |
| `AWS_STORAGE_BUCKET_NAME` | ❌ | - | S3 bucket name |
| `SECURE_SSL_REDIRECT` | ❌ | False | Force HTTPS |
| `CSRF_TRUSTED_ORIGINS` | ❌ | - | CSRF trusted domains |

## Using Railway CLI

### Install Railway CLI

```bash
# npm
npm i -g @railway/cli

# Homebrew
brew install railway

# Windows (Scoop)
scoop install railway
```

### Link Project

```bash
# Link to existing project
railway link

# Or create new project
railway init
```

### Deploy

```bash
# Deploy current directory
railway up

# Run commands in Railway environment
railway run python enginel/manage.py migrate
railway run python enginel/manage.py createsuperuser

# View logs
railway logs

# Open project in browser
railway open
```

### Environment Variables

```bash
# Add variable
railway variables set SECRET_KEY=your-secret-key

# View variables
railway variables

# Run with local .env
railway run --env-file .env python manage.py runserver
```

## Post-Deployment Checklist

- [ ] All 4 services are running (App, Worker, Cron, PostgreSQL, Redis)
- [ ] Database migrations completed successfully
- [ ] Superuser account created
- [ ] Static files collected
- [ ] Public domain generated and accessible
- [ ] HTTPS enabled and working
- [ ] Environment variables configured correctly
- [ ] S3 integration working (if enabled)
- [ ] Celery worker processing tasks
- [ ] Celery beat scheduling tasks
- [ ] Logs show no errors
- [ ] Admin panel accessible
- [ ] API endpoints responding correctly
- [ ] Security headers present (check with securityheaders.com)
- [ ] Rate limiting working (test with excessive requests)

## Monitoring and Maintenance

### View Logs

```bash
# Railway dashboard
1. Click on service
2. Go to "Deployments" tab
3. View logs for latest deployment

# Railway CLI
railway logs
railway logs --service web
railway logs --service worker
railway logs --service beat
```

### Database Backups

Railway provides automatic daily backups for PostgreSQL. You can also:

1. Go to PostgreSQL service → Settings → Backups
2. Enable automatic backups
3. Download manual backups as needed

### Scaling

Railway allows you to scale services:

1. Click on service
2. Go to Settings → Resources
3. Adjust CPU, Memory, and Replicas
4. Worker and Cron services can also be scaled

### Cost Estimation

Railway pricing:
- **Free Tier**: $5 credit/month
- **Hobby Plan**: $5/month + usage
- **Pro Plan**: $20/month + usage

Typical usage for this app:
- App Service: ~$5-10/month
- Worker Service: ~$3-5/month
- Cron Service: ~$2-3/month
- PostgreSQL: ~$2-5/month
- Redis: ~$1-2/month
- **Total**: ~$13-25/month

## Troubleshooting

### App Service Won't Start

1. Check logs for errors
2. Verify all environment variables are set
3. Ensure PostgreSQL and Redis are running
4. Check Dockerfile builds successfully locally
5. Verify `ALLOWED_HOSTS` includes Railway domain

### Worker/Cron Service Not Processing

1. Verify Redis connection: `railway run python -c "import redis; r=redis.from_url('$REDIS_URL'); print(r.ping())"`
2. Check worker logs for connection errors
3. Ensure all environment variables match App Service
4. Test Celery locally: `celery -A enginel worker --loglevel=debug`

### Database Connection Errors

1. Verify PostgreSQL service is healthy
2. Check database variables are correctly referenced
3. Test connection: `railway run python enginel/manage.py dbshell`
4. Ensure migrations are up to date

### Static Files Not Loading

1. Run `railway run python enginel/manage.py collectstatic --noinput`
2. Verify `STATIC_ROOT` is set correctly
3. Check WhiteNoise is in MIDDLEWARE
4. Ensure `STORAGES` configuration is correct

### Rate Limiting Issues

1. Check Redis connection
2. Verify `REDIS_URL` environment variable
3. Test Redis: `railway run python -c "from django.core.cache import cache; cache.set('test', 'works', 60); print(cache.get('test'))"`
4. Review security middleware logs

## Security Recommendations

1. **Change DEBUG to False** in production
2. **Set strong SECRET_KEY** (use `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`)
3. **Enable SECURE_SSL_REDIRECT**
4. **Configure CSRF_TRUSTED_ORIGINS** with your actual domains
5. **Set up IP whitelisting** if needed
6. **Enable S3 for file storage** (don't use local storage in production)
7. **Configure email notifications** for security events
8. **Review security headers** at securityheaders.com
9. **Set up monitoring** and alerts
10. **Regular backups** of database

## Support and Resources

- **Railway Documentation**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **Enginel Issues**: https://github.com/Dxcraig/Enginel/issues
- **Django Deployment**: https://docs.djangoproject.com/en/stable/howto/deployment/
- **Security Checklist**: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

## Next Steps

1. Set up custom domain (if needed)
2. Configure email notifications
3. Set up monitoring and alerts
4. Implement CI/CD pipeline
5. Configure automated backups
6. Set up staging environment
7. Add health check endpoints
8. Configure logging aggregation
9. Set up performance monitoring
10. Review and optimize resource usage
