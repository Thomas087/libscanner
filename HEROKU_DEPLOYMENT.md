# Heroku Deployment Guide for Background Tasks

This guide explains how to deploy your Django app with Celery background tasks to Heroku.

## 🚀 **Quick Setup**

### **1. Install Redis Addon**

```bash
# For development (free tier)
heroku addons:create heroku-redis:mini

# For production (recommended)
heroku addons:create heroku-redis:premium-0
```

### **2. Deploy Your Code**

```bash
git add .
git commit -m "Add background task support"
git push heroku main
```

### **3. Run Migrations**

```bash
heroku run python manage.py migrate
```

### **4. Start Worker Process**

```bash
heroku ps:scale worker=1
```

### **5. Test the Setup**

```bash
# Test Redis connection
heroku run python manage.py test_redis

# Test starting a task
heroku run python manage.py start_animal_task --prefecture Morbihan
```

## 🔧 **Configuration Details**

### **Environment Variables (Automatic)**

Heroku automatically sets these when you add Redis:

- `REDIS_URL` - Your Redis connection string
- Your Django settings use this automatically

### **Celery Configuration**

Your settings are already optimized for Heroku:

```python
# Uses REDIS_URL from Heroku
CELERY_BROKER_URL = os.environ.get('REDISCLOUD_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDISCLOUD_URL', 'redis://localhost:6379/0')

# Heroku-specific optimizations
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
```

### **Procfile Configuration**

```
web: gunicorn libscanner.wsgi --log-file - --bind 0.0.0.0:$PORT
worker: celery -A libscanner worker --loglevel=info --concurrency=1 --without-gossip --without-mingle --without-heartbeat
release: python manage.py migrate --noinput
```

## 📊 **Monitoring Commands**

### **Check Application Status**

```bash
# Check all processes
heroku ps

# Check worker logs
heroku logs --tail --dyno=worker

# Check web logs
heroku logs --tail --dyno=web
```

### **Test Redis Connection**

```bash
# Test Redis and Celery setup
heroku run python manage.py test_redis

# Test task creation
heroku run python manage.py start_animal_task --prefecture Morbihan
```

### **Scale Workers**

```bash
# Start worker
heroku ps:scale worker=1

# Stop worker
heroku ps:scale worker=0

# Scale to multiple workers
heroku ps:scale worker=2
```

## 🎯 **Admin Interface on Heroku**

### **Access Django Admin**

1. **Visit:** `https://your-app.herokuapp.com/admin/scraper/scrapingtask/`
2. **Start tasks** using the web interface
3. **Monitor progress** in real-time
4. **Stop tasks** with one click

### **Admin Features on Heroku**

- ✅ **Start tasks** - Use the quick launch buttons
- ✅ **Monitor progress** - Real-time progress bars
- ✅ **Stop tasks** - One-click cancellation
- ✅ **View results** - Complete task history
- ✅ **Database persistence** - All data saved

## 💰 **Cost Considerations**

### **Free Tier Limitations**

- **Worker dynos sleep** after 30 minutes of inactivity
- **Redis Mini** has 25MB limit
- **No 24/7 background processing**

### **Production Recommendations**

```bash
# Use premium Redis for production
heroku addons:create heroku-redis:premium-0

# Use standard dyno for better performance
heroku ps:scale worker=1:standard-1x
```

### **Cost Breakdown**

- **Worker dyno:** ~$7/month (basic) or ~$25/month (standard)
- **Redis Mini:** Free (25MB limit)
- **Redis Premium:** ~$15/month (unlimited)

## 🔍 **Troubleshooting**

### **Common Issues**

**1. Worker Not Starting**

```bash
# Check worker logs
heroku logs --tail --dyno=worker

# Restart worker
heroku ps:restart worker
```

**2. Redis Connection Issues**

```bash
# Test Redis connection
heroku run python manage.py test_redis

# Check Redis info
heroku redis:info
```

**3. Tasks Not Executing**

```bash
# Check if worker is running
heroku ps

# Check Celery status
heroku run python manage.py shell -c "from celery import current_app; print(current_app.control.inspect().active())"
```

### **Debug Commands**

```bash
# Test Redis connection
heroku run python manage.py test_redis

# Check environment variables
heroku config

# View Redis usage
heroku redis:info

# Check worker status
heroku ps
```

## 🚀 **Production Deployment**

### **Recommended Production Setup**

```bash
# 1. Install premium Redis
heroku addons:create heroku-redis:premium-0

# 2. Use standard worker dyno
heroku ps:scale worker=1:standard-1x

# 3. Set up monitoring
heroku addons:create newrelic:wayne
```

### **Environment Variables for Production**

```bash
# Disable eager execution (enable background tasks)
heroku config:set CELERY_TASK_ALWAYS_EAGER=False

# Set timezone
heroku config:set TZ=Europe/Paris
```

## 📈 **Performance Optimization**

### **Worker Configuration**

- **Concurrency:** Set to 1 for memory efficiency
- **Memory:** Use standard dynos for better performance
- **Scaling:** Scale workers based on task volume

### **Redis Optimization**

- **Premium Redis:** For production workloads
- **Connection pooling:** Automatic with redis-py
- **Memory management:** Monitor usage with `heroku redis:info`

## ✅ **Verification Checklist**

After deployment, verify:

- [ ] Redis addon installed: `heroku addons`
- [ ] Worker process running: `heroku ps`
- [ ] Redis connection working: `heroku run python manage.py test_redis`
- [ ] Admin interface accessible: `https://your-app.herokuapp.com/admin/`
- [ ] Tasks can be started: Use admin interface
- [ ] Tasks execute properly: Check worker logs
- [ ] Results are saved: Check database

## 🎉 **Success!**

Your Django app with Celery background tasks is now running on Heroku! You can:

- **Start tasks** from the web interface
- **Monitor progress** in real-time
- **Stop tasks** when needed
- **View results** in the admin interface
- **Scale workers** based on demand

The system is production-ready with proper error handling, database persistence, and monitoring capabilities!
