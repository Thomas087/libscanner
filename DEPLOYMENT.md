# Heroku Deployment Guide

## Prerequisites

- Heroku CLI installed
- Git repository initialized
- PostgreSQL database (Heroku Postgres addon)

## Deployment Steps

### 1. Install Heroku CLI

```bash
# macOS
brew install heroku/brew/heroku

# Or download from https://devcenter.heroku.com/articles/heroku-cli
```

### 2. Login to Heroku

```bash
heroku login
```

### 3. Create Heroku App

```bash
heroku create your-app-name
```

### 4. Add PostgreSQL Addon

```bash
heroku addons:create heroku-postgresql:mini
```

### 5. Set Environment Variables

```bash
# Generate a new secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Set environment variables
heroku config:set SECRET_KEY=your-generated-secret-key
heroku config:set DEBUG=False
```

### 6. Deploy to Heroku

```bash
git add .
git commit -m "Prepare for Heroku deployment"
git push heroku main
```

### 7. Run Migrations

```bash
heroku run python manage.py migrate
```

### 8. Create Superuser (Optional)

```bash
heroku run python manage.py createsuperuser
```

### 9. Collect Static Files

```bash
heroku run python manage.py collectstatic --noinput
```

## Environment Variables

Required environment variables for production:

- `SECRET_KEY`: Django secret key (generate a new one for production)
- `DEBUG`: Set to `False` for production
- `DATABASE_URL`: Automatically set by Heroku Postgres addon
- `ALLOWED_HOSTS`: Your domain names (comma-separated)

## Local Development with Environment Variables

Create a `.env` file in your project root:

```
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgresql://thomas_duqi@localhost:5432/libscanner
```

## Troubleshooting

### Static Files Issues

If static files don't load properly:

```bash
heroku run python manage.py collectstatic --noinput
```

### Database Connection Issues

Check your DATABASE_URL:

```bash
heroku config:get DATABASE_URL
```

### Logs

View application logs:

```bash
heroku logs --tail
```
