# Deployment Guide

This guide covers Docker deployment, production setup, and CI/CD for Bob Digital Investigator.

---

## Docker Deployment (Recommended)

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM
- At least 10GB disk space

### Quick Start

```bash
# Clone the repository
git clone https://github.com/juanvictorqwerty/Bob-Digital-Investigator.git
cd Bob-Digital-Investigator

# Copy environment template
cp server/.env.example server/.env

# Edit server/.env with your API keys
nano server/.env

# Start all services
docker compose up --build -d

# Check logs
docker compose logs -f
```

### Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Grafana Dashboard**: http://localhost:3001
- **Prometheus**: http://localhost:9090
- **Django Admin**: http://localhost:8000/admin/

### Stop Services

```bash
docker compose down
```

### Stop and Remove Volumes (Clean Slate)

```bash
docker compose down -v
```

### Rebuild After Code Changes

```bash
docker compose up --build -d
```

---

## Production Deployment

### Server Requirements

- **OS**: Ubuntu 20.04+ or Debian 11+
- **RAM**: 4GB minimum (8GB recommended)
- **CPU**: 2 cores minimum (4 cores recommended)
- **Disk**: 20GB minimum (SSD recommended)
- **Network**: Static IP or domain name

### Production Setup Steps

#### 1. Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
sudo apt install docker-compose -y

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (optional, avoids sudo)
sudo usermod -aG docker $USER
```

#### 2. Clone Repository

```bash
# Clone to production directory
git clone https://github.com/juanvictorqwerty/Bob-Digital-Investigator.git /opt/bob
cd /opt/bob

# Set permissions
sudo chown -R $USER:$USER /opt/bob
```

#### 3. Configure Environment

```bash
# Copy and edit .env
cp server/.env.example server/.env
nano server/.env
```

**Critical production settings:**
- Set `DEBUG=False`
- Use strong `DJANGO_SECRET_KEY`
- Use strong database password
- Set `ALLOWED_HOSTS` to your domain
- Set `FRONTEND_URL` to your domain
- Add all API keys

#### 4. Configure Firewall

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

#### 5. Start Services

```bash
docker compose up --build -d

# Verify all services are running
docker compose ps

# Check logs for errors
docker compose logs -f
```

#### 6. Set Up Nginx (Optional but Recommended)

For production, use Nginx as reverse proxy with SSL:

```bash
# Install Nginx
sudo apt install nginx -y

# Configure site
sudo nano /etc/nginx/sites-available/bob
```

**Example Nginx config:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Client
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Admin
    location /admin/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Grafana
    location /grafana/ {
        proxy_pass http://localhost:3000/;
        proxy_set_header Host $host;
    }
}
```

#### 7. Set Up SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

---

## CI/CD with GitHub Actions

### Workflows

The project includes two GitHub Actions workflows:

#### 1. CI - Tests (`.github/workflows/test.yml`)

**Triggers:**
- Push to `main` branch
- Pull requests to `main` branch

**Jobs:**
- **client-tests**: Runs Next.js tests with Bun
- **server-tests**: Runs Django tests with PostgreSQL and Redis

**Process:**
1. Checkout code
2. Set up Bun/Python
3. Install dependencies
4. Create test .env file
5. Run migrations
6. Run tests

#### 2. CD - Deploy (`.github/workflows/deploy.yml`)

**Triggers:**
- Push to `main` branch (only if CI passes)

**Process:**
1. Checkout code
2. SSH into production server
3. Pull latest code
4. Write .env from GitHub Secret
5. Rebuild and restart Docker containers
6. Prune unused Docker images

### Required GitHub Secrets

Configure these in **GitHub Repository → Settings → Secrets and variables → Actions**:

| Secret | Description | Example |
|--------|-------------|---------|
| `SERVER_HOST` | Production server IP/hostname | `95.111.225.85` |
| `SERVER_USER` | SSH username | `root` |
| `SSH_PRIVATE_KEY` | SSH private key for authentication | `-----BEGIN RSA PRIVATE KEY-----...` |
| `SERVER_DEPLOY_PATH` | Path to project on server | `/opt/bob` |
| `ENV_FILE` | Complete production .env content | See below |

#### Setting Up ENV_FILE Secret

**Option 1: Using GitHub CLI**

```bash
# Read from local .env file
gh secret set ENV_FILE < server/.env

# Or set from stdin
cat server/.env | gh secret set ENV_FILE
```

**Option 2: Using GitHub Web UI**

1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `ENV_FILE`
4. Value: Paste entire contents of your production `.env` file
5. Click "Add secret"

**Option 3: Using GitHub CLI with multiple secrets**

```bash
# Set all secrets at once
gh secret set SERVER_HOST -b "95.111.225.85"
gh secret set SERVER_USER -b "root"
gh secret set SSH_PRIVATE_KEY < ~/.ssh/id_rsa
gh secret set SERVER_DEPLOY_PATH -b "/opt/bob"
gh secret set ENV_FILE < server/.env
```

### Deployment Flow

```
Push to main
    ↓
CI Tests Run (client + server)
    ↓
If tests pass:
    ↓
CD Deploy Workflow Triggers
    ↓
SSH into production server
    ↓
git pull origin main
    ↓
Write .env from ENV_FILE secret
    ↓
docker compose up --build --remove-orphans -d
    ↓
Prune old Docker images
    ↓
Deployment Complete
```

### Manual Deployment

If you need to deploy manually:

```bash
# SSH into server
ssh root@95.111.225.85

# Navigate to project
cd /opt/bob

# Pull latest code
git pull origin main

# Rebuild and restart
docker compose up --build --remove-orphans -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

---

## Docker Configuration

### Docker Compose Services

**File:** `docker-compose.yml`

| Service | Image | Ports | Description |
|---------|-------|-------|-------------|
| db | postgres:latest | Internal | PostgreSQL database |
| redis | redis:7-alpine | Internal | Cache and message broker |
| searxng | searxng/searxng:latest | 8888:8080 | Metasearch engine |
| django | Custom build | 8000:8000 | Django REST API |
| celery-worker | Custom build | Internal | Celery task worker |
| client | Custom build | 3000:3000 | Next.js frontend |
| prometheus | prom/prometheus:latest | 9090:9090 | Metrics collector |
| grafana | grafana/grafana:10.4.2 | 3001:3000 | Dashboard |
| nginx | nginx:alpine | 80:80 | Reverse proxy |

### Docker Volumes

| Volume | Purpose |
|--------|---------|
| `postgresql_data` | PostgreSQL data persistence |
| `redis_data` | Redis data persistence |
| `staticfiles` | Django static files |
| `prometheus_data` | Prometheus metrics storage |
| `grafana_data` | Grafana dashboard storage |

### Multi-Stage Builds

#### Client (Next.js)

**Stages:**
1. **deps**: Install production dependencies
2. **build**: Install dev dependencies and build Next.js
3. **final**: Minimal runtime image with only production artifacts

**Benefits:**
- Smaller final image size
- Faster deployments
- Reduced attack surface

#### Server (Django)

**Stages:**
1. **base**: Install system dependencies
2. **deps**: Install Python dependencies
3. **final**: Copy only necessary files

**Benefits:**
- Optimized image size
- Layer caching for faster rebuilds

---

## Environment Variables in Production

### Using GitHub Secrets (Recommended)

The deployment workflow uses the `ENV_FILE` secret to write the `.env` file on the server:

```yaml
# In .github/workflows/deploy.yml
cat << 'EOF' > .env
${{ secrets.ENV_FILE }}
EOF
```

**Advantages:**
- Secrets never exposed in logs
- Centralized secret management
- Easy rotation

### Using Server Environment Variables

Alternatively, set environment variables directly in `docker-compose.yml`:

```yaml
services:
  django:
    environment:
      - DB_NAME=${DB_NAME}
      - DB_PASSWORD=${DB_PASSWORD}
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
```

**Note:** Less secure than GitHub Secrets for CI/CD.

---

## Monitoring Production

### Health Checks

```bash
# Check all services are running
docker compose ps

# Check service health
docker compose exec django curl -f http://localhost:8000/health/ || echo "Django unhealthy"
docker compose exec redis redis-cli ping
docker compose exec db pg_isready -U bob
```

### Logs

```bash
# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f django
docker compose logs -f celery-worker
docker compose logs -f client

# View last 100 lines
docker compose logs --tail=100 django
```

### Resource Usage

```bash
# Check container resource usage
docker stats

# Check disk usage
docker system df

# Prune unused resources
docker system prune -af
```

---

## Backup Strategy

### Database Backups

```bash
# Manual backup
docker compose exec db pg_dump -U bob bob > backup_$(date +%Y%m%d).sql

# Restore
docker compose exec -T db psql -U bob bob < backup_20250115.sql
```

### Automated Backups (Cron)

```bash
# Add to crontab (daily at 2 AM)
0 2 * * * cd /opt/bob && docker compose exec db pg_dump -U bob bob > backups/bob_$(date +\%Y\%m\%d).sql

# Keep only last 7 days
0 3 * * * find /opt/bob/backups -name "bob_*.sql" -mtime +7 -delete
```

### Volume Backups

```bash
# Backup all volumes
docker run --rm -v bob_postgresql_data:/data -v /opt/bob/backups:/backup alpine tar cvf /backup/postgresql_data.tar /data

# Restore volume
docker run --rm -v bob_postgresql_data:/data -v /opt/bob/backups:/backup alpine tar xvf /backup/postgresql_data.tar -C /data
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker compose logs

# Common issues:
# - Port already in use: Change ports in docker-compose.yml
# - Out of disk space: docker system prune -af
# - Permission errors: Check file permissions
```

### Database Migration Issues

```bash
# Run migrations manually
docker compose exec django python manage.py migrate

# Check migration status
docker compose exec django python manage.py showmigrations
```

### Celery Tasks Stuck

```bash
# Restart Celery worker
docker compose restart celery-worker

# Check Celery logs
docker compose logs celery-worker

# Clear Celery queue (use with caution!)
docker compose exec django python manage.py shell -c "from celery import current_app; current_app.control.purge()"
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Increase Celery concurrency (in docker-compose.yml)
command: celery -A _Project worker -l info --concurrency=8

# Scale Celery workers
docker compose up -d --scale celery-worker=4
```

---

## Security Best Practices

1. **Never commit `.env` to git** (already in .gitignore)
2. **Use strong passwords** for database and admin
3. **Enable HTTPS** with Let's Encrypt
4. **Set `DEBUG=False`** in production
5. **Restrict `ALLOWED_HOSTS`** to your domain
6. **Use GitHub Secrets** for deployment
7. **Regular backups** of database
8. **Keep Docker images updated**
9. **Monitor logs** for suspicious activity
10. **Use firewall** to restrict access

---

## Updates and Maintenance

### Updating the Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose up --build -d

# Run migrations if needed
docker compose exec django python manage.py migrate
```

### Updating Dependencies

```bash
# Update Python dependencies
# Edit server/requirements.txt, then:
docker compose build django
docker compose up -d django

# Update Node dependencies
# Edit client/package.json, then:
docker compose build client
docker compose up -d client
```

### Updating Docker Images

```bash
# Pull latest base images
docker compose pull

# Rebuild with latest images
docker compose up --build -d