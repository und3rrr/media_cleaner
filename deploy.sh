#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════════
# АВТОМАТИЧЕСКИЙ СКРИПТ РАЗВЕРТЫВАНИЯ MEDIA CLEANER
# ═══════════════════════════════════════════════════════════════════════════════
# Использование: 
#   sudo bash deploy.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -e  # Выйти при первой ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
DOMAIN="${1:-video-cleaner.example.com}"
EMAIL="${2:-admin@example.com}"
APP_DIR="/home/media_cleaner"
APP_USER="media_cleaner"
PYTHON_VERSION="3.11"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}РАЗВЕРТЫВАНИЕ MEDIA CLEANER НА СЕРВЕРЕ${NC}"
echo -e "${BLUE}Домен: $DOMAIN${NC}"
echo -e "${BLUE}Email: $EMAIL${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Проверка прав администратора
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] Этот скрипт должен быть запущен от root!${NC}"
   exit 1
fi

# Функция для вывода сообщений
log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# ═══════════════════════════════════════════════════════════════════════════════
# ЭТАП 1: ОБНОВЛЕНИЕ СИСТЕМЫ
# ═══════════════════════════════════════════════════════════════════════════════

log_info "ЭТАП 1/6: Обновление системы..."
apt update
apt upgrade -y
log_info "Система обновлена"

# ═══════════════════════════════════════════════════════════════════════════════
# ЭТАП 2: УСТАНОВКА ЗАВИСИМОСТЕЙ
# ═══════════════════════════════════════════════════════════════════════════════

log_info "ЭТАП 2/6: Установка зависимостей..."

apt install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-dev \
    python3-pip \
    build-essential \
    curl \
    wget \
    git \
    ffmpeg \
    nginx \
    certbot \
    python3-certbot-nginx \
    supervisor \
    htop

log_info "Зависимости установлены"

# Проверка версий
python${PYTHON_VERSION} --version
ffmpeg -version | head -1
nginx -v

# ═══════════════════════════════════════════════════════════════════════════════
# ЭТАП 3: СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ И ПАПОК
# ═══════════════════════════════════════════════════════════════════════════════

log_info "ЭТАП 3/6: Настройка пользователя и папок..."

# Создайте пользователя (если не существует)
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash -d $APP_DIR $APP_USER
    log_info "Создан пользователь $APP_USER"
else
    log_warn "Пользователь $APP_USER уже существует"
fi

# Убедитесь что папка принадлежит пользователю
if [ -d "$APP_DIR" ]; then
    chown -R $APP_USER:$APP_USER $APP_DIR
else
    mkdir -p $APP_DIR
    chown -R $APP_USER:$APP_USER $APP_DIR
fi

# Создайте необходимые папки
mkdir -p $APP_DIR/uploads
mkdir -p $APP_DIR/logs
mkdir -p $APP_DIR/temp
mkdir -p $APP_DIR/backups
chown -R $APP_USER:$APP_USER $APP_DIR/{uploads,logs,temp,backups}
chmod 755 $APP_DIR/{uploads,logs,temp,backups}

log_info "Папки созданы в $APP_DIR"

# ═══════════════════════════════════════════════════════════════════════════════
# ЭТАП 4: РАЗВЕРТЫВАНИЕ ПРИЛОЖЕНИЯ
# ═══════════════════════════════════════════════════════════════════════════════

log_info "ЭТАП 4/6: Развертывание приложения..."

cd $APP_DIR

# Проверьте наличие requirements.txt
if [ ! -f "requirements.txt" ]; then
    log_error "requirements.txt не найден в $APP_DIR"
    log_error "Пожалуйста, скопируйте файлы проекта в $APP_DIR перед запуском"
    exit 1
fi

# Создайте виртуальное окружение
su - $APP_USER -c "python${PYTHON_VERSION} -m venv venv"
su - $APP_USER -c "source venv/bin/activate && pip install --upgrade pip setuptools wheel"

# Установите зависимости
su - $APP_USER -c "source venv/bin/activate && pip install -r requirements.txt"

log_info "Приложение установлено в $APP_DIR"

# ═══════════════════════════════════════════════════════════════════════════════
# ЭТАП 5: СОЗДАНИЕ SYSTEMD СЕРВИСОВ
# ═══════════════════════════════════════════════════════════════════════════════

log_info "ЭТАП 5/6: Создание systemd сервисов..."

# Сервис для FastAPI
cat > /etc/systemd/system/media-cleaner-api.service <<EOF
[Unit]
Description=Media Cleaner API Server (FastAPI)
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/python -m uvicorn server_app:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=media-cleaner-api

[Install]
WantedBy=multi-user.target
EOF

# Сервис для Flask
cat > /etc/systemd/system/media-cleaner-web.service <<EOF
[Unit]
Description=Media Cleaner Web Interface (Flask)
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/python -m gunicorn \\
    --workers 4 \\
    --worker-class sync \\
    --bind 127.0.0.1:5000 \\
    --access-logfile $APP_DIR/logs/gunicorn_access.log \\
    --error-logfile $APP_DIR/logs/gunicorn_error.log \\
    --log-level info \\
    main:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=media-cleaner-web

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable media-cleaner-api.service
systemctl enable media-cleaner-web.service
systemctl start media-cleaner-api.service
systemctl start media-cleaner-web.service

log_info "Systemd сервисы созданы и запущены"

sleep 2

# Проверьте статус
if systemctl is-active --quiet media-cleaner-api; then
    log_info "FastAPI сервис работает"
else
    log_error "FastAPI сервис НЕ работает! Проверьте логи:"
    journalctl -u media-cleaner-api -n 20
fi

if systemctl is-active --quiet media-cleaner-web; then
    log_info "Flask сервис работает"
else
    log_error "Flask сервис НЕ работает! Проверьте логи:"
    journalctl -u media-cleaner-web -n 20
fi

# ═══════════════════════════════════════════════════════════════════════════════
# ЭТАП 6: КОНФИГУРАЦИЯ NGINX И SSL
# ═══════════════════════════════════════════════════════════════════════════════

log_info "ЭТАП 6/6: Конфигурация Nginx и SSL..."

# Создайте Nginx конфиг
cat > /etc/nginx/sites-available/media-cleaner <<'NGINXEOF'
upstream media_cleaner_api {
    server 127.0.0.1:8000;
}

upstream media_cleaner_web {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    listen [::]:80;
    server_name DOMAIN_PLACEHOLDER;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name DOMAIN_PLACEHOLDER;

    ssl_certificate /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    client_max_body_size 2G;
    
    location / {
        proxy_pass http://media_cleaner_web;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 600s;
    }

    location /api/ {
        proxy_pass http://media_cleaner_api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 600s;
    }

    location /static/ {
        alias APP_DIR_PLACEHOLDER/static/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads/ {
        alias APP_DIR_PLACEHOLDER/uploads/;
        expires 7d;
    }

    access_log /var/log/nginx/media-cleaner-access.log;
    error_log /var/log/nginx/media-cleaner-error.log;
}
NGINXEOF

# Замените плейсхолдеры
sed -i "s|DOMAIN_PLACEHOLDER|$DOMAIN|g" /etc/nginx/sites-available/media-cleaner
sed -i "s|APP_DIR_PLACEHOLDER|$APP_DIR|g" /etc/nginx/sites-available/media-cleaner

# Создайте символическую ссылку
ln -sf /etc/nginx/sites-available/media-cleaner /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Проверьте синтаксис Nginx
if nginx -t 2>&1 | grep -q "successful"; then
    log_info "Nginx конфиг OK"
else
    log_error "Ошибка в Nginx конфиге!"
    nginx -t
    exit 1
fi

# Перезагрузите Nginx
systemctl restart nginx

# Получите SSL сертификат
log_warn "Получение SSL сертификата для $DOMAIN..."
mkdir -p /var/www/certbot

certbot certonly --standalone \
    -d $DOMAIN \
    --email $EMAIL \
    --non-interactive \
    --agree-tos \
    --rsa-key-size 4096 \
    2>&1 || log_error "Не удалось получить сертификат. Проверьте что домен правильно настроен!"

# Перезагрузите Nginx с SSL
systemctl reload nginx

log_info "Nginx и SSL конфигурированы"

# ═══════════════════════════════════════════════════════════════════════════════
# ФИНАЛЬНАЯ ПРОВЕРКА
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО УСПЕШНО!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}СИСТЕМА ЗАПУЩЕНА И ГОТОВА К ИСПОЛЬЗОВАНИЮ${NC}"
echo ""
echo "Доступ к приложению:"
echo -e "  ${GREEN}https://$DOMAIN${NC}"
echo ""
echo "Управление сервисами:"
echo "  Посмотрите логи API:    ${YELLOW}sudo journalctl -u media-cleaner-api -f${NC}"
echo "  Посмотрите логи Web:    ${YELLOW}sudo journalctl -u media-cleaner-web -f${NC}"
echo "  Посмотрите логи Nginx:  ${YELLOW}sudo tail -f /var/log/nginx/media-cleaner-error.log${NC}"
echo ""
echo "Полезные команды:"
echo "  Перезагрузить сервисы:  ${YELLOW}sudo systemctl restart media-cleaner-api media-cleaner-web${NC}"
echo "  Остановить приложение:  ${YELLOW}sudo systemctl stop media-cleaner-api media-cleaner-web${NC}"
echo "  Проверить статус:       ${YELLOW}sudo systemctl status media-cleaner-api media-cleaner-web nginx${NC}"
echo ""

# Тестовый запрос
echo -e "${YELLOW}Тестирование API...${NC}"
sleep 2

if curl -s http://127.0.0.1:8000/docs > /dev/null; then
    echo -e "${GREEN}✓ API доступен на http://127.0.0.1:8000${NC}"
else
    echo -e "${RED}✗ API недоступен${NC}"
fi

if curl -s http://127.0.0.1:5000 > /dev/null; then
    echo -e "${GREEN}✓ Flask доступен на http://127.0.0.1:5000${NC}"
else
    echo -e "${RED}✗ Flask недоступен${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
