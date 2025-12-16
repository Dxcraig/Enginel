# Railway Deployment Guide for Enginel

This guide covers deploying the Enginel Django application to Railway with PostgreSQL, Redis, and Celery workers.

## Architecture

The deployment uses a **Majestic Monolith** architecture with separate services:

```
┌─────────────────────────────────────────────────────────────┐
│                    Railway Project                           │
├─────────────────┬──────────────┬──────────────┬─────────────┤
│   App Service   │ Worker Service│ Beat Service │  Databases  │
│   (Web/API)     │   (Celery)    │ (Celery Beat)│ (PG + Redis)│
│                 │               │              │             │
│ • Django API    │ • Background  │ • Scheduled  │ • PostgreSQL│
│ • REST API      │   tasks       │   tasks      │ • Redis     │
│ • Admin panel   │ • File        │ • Periodic   │             │
│ • Static files  │   processing  │   jobs       │             │
└─────────────────┴──────────────┴──────────────┴─────────────┘
```

## Prerequisites

1. **Railway Account**: Sign up at https://railway.app
2. **Railway CLI** (optional but recommended):
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   
   # Login to Railway
   railway login
   ```

3. **GitHub Repository**: Push your code to GitHub
4. **AWS S3 Bucket**: For file storage (CAD files, designs)
5. **Email Service**: SendGrid, Mailgun, or similar (optional)

## Step-by-Step Deployment

### 1. Create New Railway Project

**Option A: Using Railway Dashboard**
1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your repository
4. Railway will detect it as a Django app

**Option B: Using Railway CLI**
```bash
cd /path/to/Enginel
railway init
railway link
```

### 2. Add Database Services

Railway provides managed PostgreSQL and Redis databases that automatically configure connection URLs.

#### Add PostgreSQL Database
1. In your Railway project, click **"Create"** button
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway automatically provisions the database
4. Connection variables are automatically created:
   - `PGHOST`
   - `PGPORT`
   - `PGUSER`
   - `PGPASSWORD`
   - `PGDATABASE`
   - `DATABASE_URL` (complete connection string)

#### Add Redis Database
1. Click **"Create"** button again
2. Select **"Database"** → **"Add Redis"**
3. Railway automatically provisions Redis
4. Connection variables are automatically created:
   - `REDIS_URL` (complete connection string)
   - `REDIS_PRIVATE_URL`

**Important**: Your app will automatically reference these database variables using Railway's variable referencing syntax: `${{Postgres.PGDATABASE}}`, `${{Redis.REDIS_URL}}`, etc.

### 3. Configure App Service (Web)

This service runs your Django web application.

1. **Service Setup**:
   - Railway auto-creates a service when you deploy from GitHub
   - Rename it to "App Service" for clarity: Click service → Settings → Service Name

2. **Connect GitHub Repo**: 
   - Settings → Source → Connect your repository
   - Select branch (usually `main`)

3. **Build Configuration**:
   - Railway auto-detects `railway.json` or `railway.toml`
   - Build command: `python -m pip install -r enginel/requirements.txt`
   - Start command: `cd enginel && python manage.py collectstatic --noinput && gunicorn enginel.wsgi --bind 0.0.0.0:$PORT --workers 4`

4. **Add Environment Variables**:
   
   Click **Variables** tab → **Raw Editor** and add:
   
   ```bash
   # Core Django Settings
   SECRET_KEY=<generate-new-secret-key-here>
   DEBUG=False
   
   # Database - Reference Railway's PostgreSQL service
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   PGDATABASE=${{Postgres.PGDATABASE}}
   PGUSER=${{Postgres.PGUSER}}
   PGPASSWORD=${{Postgres.PGPASSWORD}}
   PGHOST=${{Postgres.PGHOST}}
   PGPORT=${{Postgres.PGPORT}}
   
   # Redis - Reference Railway's Redis service
   REDIS_URL=${{Redis.REDIS_URL}}
   
   # Celery (uses Redis)
   CELERY_BROKER_URL=${{Redis.REDIS_URL}}
   CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}
   
   # AWS S3 Storage
   AWS_ACCESS_KEY_ID=your-aws-access-key-id
   AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
   AWS_STORAGE_BUCKET_NAME=your-bucket-name
   AWS_S3_REGION_NAME=us-east-1
   USE_S3=True
   
   # Security Settings
   SECURE_SSL_REDIRECT=True
   SECURE_HSTS_SECONDS=31536000
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   
   # Email (Optional - configure if needed)
   EMAIL_HOST=smtp.sendgrid.net
   EMAIL_HOST_USER=apikey
   EMAIL_HOST_PASSWORD=your-sendgrid-api-key
   DEFAULT_FROM_EMAIL=noreply@yourdomain.com
   ```

5. **Deploy**: Click **"Deploy"** button

### 4. Run Database Migrations

After the App Service deploys successfully, you need to run migrations **once**:

```bash
# Using Railway CLI
railway run python enginel/manage.py migrate

# Create superuser
railway run python enginel/manage.py createsuperuser
```

### 5. Create Celery Worker Service

This service processes background tasks (file processing, notifications, etc.)

1. Click **"Create"** → **"Empty Service"**
2. Name it **"Worker Service"**
3. **Settings** tab:
   - **Source**: Connect the **same GitHub repository**
   - **Root Directory**: Leave blank (uses repository root)
   - **Custom Start Command**:
     ```bash
     cd enginel && celery -A enginel worker --loglevel=info --concurrency=3
     ```

4. **Variables** tab:
   - Copy **all variables** from App Service
   - OR add them manually in Raw Editor (same as App Service)
   - The Worker needs access to the database and Redis

5. **Deploy**: Click **"Deploy"**

**Note**: The Worker service shares the same codebase but runs Celery instead of Django.

### 6. Create Celery Beat Service (Scheduled Tasks)

This service handles periodic/scheduled tasks (cleanup, reports, digest emails, etc.)

1. Click **"Create"** → **"Empty Service"**
2. Name it **"Beat Service"**
3. **Settings** tab:
   - **Source**: Connect the **same GitHub repository**
   - **Root Directory**: Leave blank
   - **Custom Start Command**:
     ```bash
     cd enginel && celery -A enginel beat --loglevel=info
     ```

4. **Variables** tab:
   - Copy **all variables** from App Service
   - The Beat service also needs database and Redis access

5. **Deploy**: Click **"Deploy"**

**Important**: Only run **ONE** Celery Beat instance. Multiple beat instances will cause duplicate task execution.

### 7. Verify Services Are Running

You should now have **5 services** in your Railway project:

```
┌─────────────────────────────────────────────────────────────┐
│                    Railway Project                           │
├─────────────────┬──────────────┬──────────────┬─────────────┤
│   App Service   │ Worker Service│ Beat Service │  Databases  │
│   ✓ Running     │   ✓ Running   │  ✓ Running   │  ✓ Healthy  │
├─────────────────┼──────────────┼──────────────┼─────────────┤
│ • Django API    │ • Celery      │ • Celery Beat│ PostgreSQL  │
│ • Gunicorn      │   Worker      │ • Schedules  │   ✓ Healthy │
│ • Port 8000     │ • 3 workers   │   tasks      │             │
│ • Public domain │ • Background  │ • No public  │   Redis     │
│                 │   tasks       │   access     │   ✓ Healthy │
└─────────────────┴──────────────┴──────────────┴─────────────┘
```

Check each service:
- **App Service**: Should show "Running" with a public URL
- **Worker Service**: Logs should show "celery@... ready"
- **Beat Service**: Logs should show "beat: Starting..."
- **PostgreSQL**: Shows "Healthy"
- **Redis**: Shows "Healthy"

## Environment Variables Reference

See `.env.railway` for complete list of environment variables.

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key (generate new!) | `django-insecure-...` |
| `DEBUG` | Debug mode (False in production) | `False` |
| `DATABASE_URL` | PostgreSQL connection | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | Redis connection | `${{Redis.REDIS_URL}}` |
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `wJalr...` |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket name | `enginel-storage` |
| `AWS_S3_REGION_NAME` | S3 region | `us-east-1` |

### Railway Auto-Set Variables

Railway automatically provides:
- `PORT` - Port to bind to
- `RAILWAY_ENVIRONMENT` - Environment name
- `RAILWAY_PUBLIC_DOMAIN` - Public domain URL
- `RAILWAY_PROJECT_ID` - Project ID
- `RAILWAY_SERVICE_ID` - Service ID

## Verification Checklist

After deployment, verify:

- [ ] All services are running (App, Worker, Beat)
- [ ] Databases are healthy (PostgreSQL, Redis)
- [ ] Public domain is accessible
- [ ] API endpoints respond: `https://your-app.railway.app/api/`
- [ ] Admin panel accessible: `https://your-app.railway.app/admin/`
- [ ] Static files load correctly
- [ ] Authentication works
- [ ] File uploads to S3 work
- [ ] Background tasks process (check Worker logs)
- [ ] Scheduled tasks run (check Beat logs)

## Monitoring & Logs

### View Logs
```bash
# All services
railway logs

# Specific service
railway logs --service "App Service"
railway logs --service "Worker Service"
railway logs --service "Beat Service"
```

### Monitor Usage
- Go to Project → Usage
- Monitor CPU, memory, network usage
- Set usage limits if needed

### Healthchecks
- Configured in `railway.json`
- Endpoint: `/api/`
- Timeout: 100 seconds

## Scaling

### Vertical Scaling (Automatic)
Railway automatically scales resources based on demand.

### Horizontal Scaling
1. Go to Service → Settings → Scaling
2. Add replicas (additional instances)
3. Configure load balancing

### Celery Workers
To increase worker concurrency:
1. Go to Worker Service → Settings
2. Update start command:
   ```bash
   cd enginel && celery -A enginel worker --loglevel=info --concurrency=10
   ```

## Common Issues & Solutions

### Issue: Static files not loading
**Solution**: 
- Ensure `collectstatic` runs in deployment
- Check `STATIC_ROOT` and `STATIC_URL` settings
- Verify WhiteNoise is in MIDDLEWARE

### Issue: Database connection errors
**Solution**:
- Verify `DATABASE_URL` is set
- Check PostgreSQL service is healthy
- Ensure `dj-database-url` is installed

### Issue: Celery tasks not processing
**Solution**:
- Check Worker Service logs
- Verify `REDIS_URL` is set correctly
- Ensure Redis service is healthy
- Check task registration in `celery.py`

### Issue: "Invalid HTTP_HOST header" error
**Solution**:
Add your domain to ALLOWED_HOSTS or CSRF_TRUSTED_ORIGINS:
```bash
ALLOWED_HOSTS=your-app.railway.app,yourdomain.com
```

### Issue: S3 upload failures
**Solution**:
- Verify AWS credentials are correct
- Check S3 bucket permissions (CORS, IAM)
- Ensure bucket region matches `AWS_S3_REGION_NAME`

## Security Best Practices

1. **Generate New Secret Key**:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

2. **Set DEBUG=False**: Always in production

3. **Enable HTTPS**: Railway provides automatic HTTPS

4. **Set Security Headers**: Already configured in `settings.py`

5. **IP Whitelisting** (optional): Configure in environment variables

6. **Monitor Security Events**: Check logs regularly

7. **Regular Updates**: Keep dependencies updated
   ```bash
   pip list --outdated
   ```

## Backup Strategy

### Database Backups
Railway automatically backs up PostgreSQL databases.

**Manual Backup**:
```bash
railway run pg_dump $DATABASE_URL > backup.sql
```

**Restore**:
```bash
railway run psql $DATABASE_URL < backup.sql
```

### S3 File Backups
Configure S3 versioning in AWS Console for automatic file versioning.

## Cost Optimization

1. **Set Usage Limits**:
   - Project → Settings → Usage Limits
   - Set monthly budget

2. **Auto-Sleep Inactive Services** (not recommended for production):
   - Service → Settings → Auto-Sleep

3. **Monitor Resource Usage**:
   - Regularly check Project → Usage
   - Optimize Celery concurrency
   - Review log retention

4. **Right-Size Services**:
   - Start with lower concurrency
   - Scale up as needed

## CI/CD with GitHub Actions

Railway auto-deploys on push to connected branch. For additional CI/CD:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      - name: Deploy
        run: railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## Support & Resources

- **Railway Docs**: https://docs.railway.com
- **Django Deployment Guide**: https://docs.railway.com/guides/django
- **Railway Discord**: https://discord.gg/railway
- **Project Status**: `railway status`

## Next Steps After Deployment

1. **Set Up Custom Domain** (optional):
   - Go to Settings → Networking → Custom Domain
   - Add your domain and configure DNS

2. **Configure Email Notifications**:
   - Test email sending
   - Set up admin notifications

3. **Enable Monitoring**:
   - Set up Sentry for error tracking
   - Configure log aggregation

4. **Load Testing**:
   - Test API endpoints
   - Verify performance under load

5. **Documentation**:
   - Document API endpoints
   - Create user guides

## Maintenance

### Regular Tasks
- Review logs weekly
- Monitor resource usage
- Update dependencies monthly
- Test backups quarterly
- Review security settings quarterly

### Deployment Updates
```bash
# Deploy new changes
git push origin main  # Auto-deploys via Railway

# Or manual deploy
railway up

# Rollback if needed
railway rollback
```

---

## Quick Reference Commands

```bash
# Login
railway login

# Link project
railway link

# Check status
railway status

# View logs
railway logs

# Run commands
railway run python enginel/manage.py <command>

# SSH into service
railway shell

# Environment variables
railway variables

# Deploy
railway up

# Rollback
railway rollback
```

---

**Questions or issues?** Check the Railway documentation or contact support.
