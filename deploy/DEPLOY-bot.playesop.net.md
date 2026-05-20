# Deploy bot-server to https://bot.playesop.net/

## 1. DNS

Create an **A record**:

```text
bot.playesop.net  ->  <your-server-public-ip>
```

Wait until DNS propagates:

```bash
dig +short bot.playesop.net
```

## 2. Server packages

```bash
sudo apt update
sudo apt install -y git curl nginx certbot python3-certbot-nginx
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Log out and log back in.

## 3. Project

```bash
cd /opt
git clone <your-repo-url> bot-poker
cd bot-poker/bot-server
cp .env.example .env
nano .env
```

Production `.env` example:

```env
BOT_SERVER_PORT=8000

REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

MAIN_BACKEND_URL=https://api.playesop.net
SERVICE_TOKEN=<same-token-as-game-backend>

BOT_JOB_QUEUE=bot_action_queue
BOT_JOB_PAYLOAD_PREFIX=poker_bot_server:job:

LOG_LEVEL=INFO
BOT_LOCK_TTL_SECONDS=15
REQUEST_TIMEOUT_SECONDS=30

DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=<strong-password>
DASHBOARD_SESSION_SECRET=<long-random-secret>
DASHBOARD_COOKIE_SECURE=true
TRUST_PROXY_HEADERS=true

POSTGRES_PASSWORD=<strong-db-password>
```

Replace `MAIN_BACKEND_URL` with the real poker API domain.

## 4. Start Docker (production compose)

```bash
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml ps
curl http://127.0.0.1:8000/health
```

Only `127.0.0.1:8000` is exposed. Redis and Postgres stay internal.

## 5. Nginx

```bash
sudo cp deploy/nginx/bot.playesop.net.conf /etc/nginx/sites-available/bot.playesop.net
sudo ln -sf /etc/nginx/sites-available/bot.playesop.net /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 6. HTTPS (Let's Encrypt)

```bash
sudo certbot --nginx -d bot.playesop.net
```

Certbot will add SSL and redirect HTTP to HTTPS.

## 7. Verify

Open:

- https://bot.playesop.net/login
- https://bot.playesop.net/dashboard
- https://bot.playesop.net/health

## 8. Game backend integration

Game backend should call bot-server at:

```text
https://bot.playesop.net/bots/action
Authorization: Bearer <SERVICE_TOKEN>
```

Bot-server calls game backend at:

```text
${MAIN_BACKEND_URL}/internal/bot-action
${MAIN_BACKEND_URL}/internal/bot-join
${MAIN_BACKEND_URL}/internal/bot-leave
```

## 9. Updates

```bash
cd /opt/bot-poker/bot-server
git pull
docker compose -f docker-compose.prod.yml up --build -d
```
