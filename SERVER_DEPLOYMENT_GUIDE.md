═══════════════════════════════════════════════════════════════════════════════
ПОЛНАЯ ИНСТРУКЦИЯ РАЗВЕРТЫВАНИЯ MEDIA CLEANER НА ВЫДЕЛЕННОМ СЕРВЕРЕ
═══════════════════════════════════════════════════════════════════════════════

ТРЕБОВАНИЯ:
- ОС: Ubuntu 20.04 LTS или выше (или другой Linux)
- Python: 3.8+ (будет установлена 3.11)
- RAM: Минимум 8GB (рекомендуется 16GB для GPU)
- Диск: 50GB+ свободного места
- Домен: Должен быть готов (например: video-cleaner.example.com)

═══════════════════════════════════════════════════════════════════════════════
ЧАСТЬ 1: ПОДГОТОВКА СЕРВЕРА
═══════════════════════════════════════════════════════════════════════════════

# 1. Подключитесь к серверу по SSH
ssh root@YOUR_SERVER_IP

# 2. Обновите систему
sudo apt update && sudo apt upgrade -y

# 3. Установите базовые инструменты
sudo apt install -y \
    build-essential \
    curl \
    wget \
    git \
    htop \
    net-tools \
    vim \
    nano

# 4. Установите Python 3.11 и pip
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    python3-dev

# 5. Установите FFmpeg (с поддержкой видеообработки)
sudo apt install -y ffmpeg

# 6. Проверьте версии
python3.11 --version
pip3 --version
ffmpeg -version

═══════════════════════════════════════════════════════════════════════════════
ЧАСТЬ 2: НАСТРОЙКА ПРИЛОЖЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

# 7. Создайте пользователя для приложения
sudo useradd -m -s /bin/bash -d /home/media_cleaner media_cleaner
sudo usermod -aG sudo media_cleaner

# 8. Переключитесь на нового пользователя
sudo su - media_cleaner

# 9. Клонируйте проект (или загрузьте файлы)
cd /home/media_cleaner
git clone https://github.com/your-repo/media_cleaner.git .
# ИЛИ скопируйте файлы через scp/SFTP:
# На локальной машине: scp -r /path/to/media_cleaner/* media_cleaner@YOUR_SERVER_IP:/home/media_cleaner/

# 10. Создайте виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate

# 11. Обновите pip
pip install --upgrade pip setuptools wheel

# 12. Установите зависимости
pip install -r requirements.txt

# 13. Проверьте установку
python -c "import torch; print('PyTorch OK')"
python -c "import cv2; print('OpenCV OK')"
python -c "import fastapi; print('FastAPI OK')"
python -c "import flask; print('Flask OK')"

# 14. Создайте директорию для загрузок и логов
mkdir -p /home/media_cleaner/uploads
mkdir -p /home/media_cleaner/logs
mkdir -p /home/media_cleaner/temp

# 15. Обновите конфиг для Linux
# Отредактируйте config.json - измените путь к ffmpeg на: "/usr/bin/ffmpeg"
nano config.json
# Найдите и измените эту строку:
# "path": "/usr/bin/ffmpeg",

═══════════════════════════════════════════════════════════════════════════════
ЧАСТЬ 3: СОЗДАНИЕ SYSTEMD СЕРВИСОВ
═══════════════════════════════════════════════════════════════════════════════

# 16. Выйдите из виртуального окружения
deactivate

# 17. Переключитесь обратно на root для создания сервисов
exit

# 18. Создайте сервис для FastAPI (порт 8000)
sudo tee /etc/systemd/system/media-cleaner-api.service > /dev/null <<EOF
[Unit]
Description=Media Cleaner API Server (FastAPI)
After=network.target

[Service]
User=media_cleaner
WorkingDirectory=/home/media_cleaner
Environment="PATH=/home/media_cleaner/venv/bin"
ExecStart=/home/media_cleaner/venv/bin/python -m uvicorn server_app:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=media-cleaner-api

[Install]
WantedBy=multi-user.target
EOF

# 19. Создайте сервис для Flask (порт 5000) 
sudo tee /etc/systemd/system/media-cleaner-web.service > /dev/null <<EOF
[Unit]
Description=Media Cleaner Web Interface (Flask)
After=network.target

[Service]
User=media_cleaner
WorkingDirectory=/home/media_cleaner
Environment="PATH=/home/media_cleaner/venv/bin"
ExecStart=/home/media_cleaner/venv/bin/python -m gunicorn \
    --workers 4 \
    --worker-class sync \
    --bind 127.0.0.1:5000 \
    --access-logfile /home/media_cleaner/logs/gunicorn_access.log \
    --error-logfile /home/media_cleaner/logs/gunicorn_error.log \
    --log-level info \
    main:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=media-cleaner-web

[Install]
WantedBy=multi-user.target
EOF

# 20. Перезагрузите systemd demon
sudo systemctl daemon-reload

# 21. Включите сервисы (чтобы стартовали при перезагрузке)
sudo systemctl enable media-cleaner-api.service
sudo systemctl enable media-cleaner-web.service

# 22. Запустите сервисы
sudo systemctl start media-cleaner-api.service
sudo systemctl start media-cleaner-web.service

# 23. Проверьте статус
sudo systemctl status media-cleaner-api.service
sudo systemctl status media-cleaner-web.service

# 24. Посмотрите логи (если ошибки)
sudo journalctl -u media-cleaner-api -f
sudo journalctl -u media-cleaner-web -f

═══════════════════════════════════════════════════════════════════════════════
ЧАСТЬ 4: УСТАНОВКА И КОНФИГУРАЦИЯ NGINX (REVERSE PROXY)
═══════════════════════════════════════════════════════════════════════════════

# 25. Установите Nginx
sudo apt install -y nginx

# 26. Создайте конфиг для Nginx
sudo tee /etc/nginx/sites-available/media-cleaner > /dev/null <<'EOF'
# API upstream (FastAPI)
upstream media_cleaner_api {
    server 127.0.0.1:8000;
}

# Web upstream (Flask)
upstream media_cleaner_web {
    server 127.0.0.1:5000;
}

# Редирект с HTTP на HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name video-cleaner.example.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS сервер
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name video-cleaner.example.com;

    # SSL сертификаты (будут установлены Certbot)
    ssl_certificate /etc/letsencrypt/live/video-cleaner.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/video-cleaner.example.com/privkey.pem;

    # SSL параметры
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Безопасность
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Лимиты
    client_max_body_size 2G;
    
    # Основной сайт (Flask на port 5000)
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

    # API (FastAPI на port 8000)
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

    # Статические файлы (кэширование)
    location /static/ {
        alias /home/media_cleaner/static/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # Загрузки видео
    location /uploads/ {
        alias /home/media_cleaner/uploads/;
        expires 7d;
    }

    # Логирование
    access_log /var/log/nginx/media-cleaner-access.log;
    error_log /var/log/nginx/media-cleaner-error.log;
}
EOF

# 27. Создайте символическую ссылку (включить сайт)
sudo ln -s /etc/nginx/sites-available/media-cleaner /etc/nginx/sites-enabled/

# 28. Удалите default конфиг (опционально)
sudo rm /etc/nginx/sites-enabled/default

# 29. Проверьте синтаксис Nginx
sudo nginx -t

# 30. Перезагрузите Nginx
sudo systemctl restart nginx

═══════════════════════════════════════════════════════════════════════════════
ЧАСТЬ 5: УСТАНОВКА SSL СЕРТИФИКАТА (LET'S ENCRYPT / CERTBOT)
═══════════════════════════════════════════════════════════════════════════════

# 31. Установите Certbot
sudo apt install -y certbot python3-certbot-nginx

# 32. Получите SSL сертификат (замените домен!)
# ВАЖНО: Убедитесь что ваш домен указывает на IP сервера!
sudo certbot certonly --nginx -d video-cleaner.example.com --email admin@example.com --non-interactive --agree-tos

# 33. Проверьте что сертификат установлен
ls -la /etc/letsencrypt/live/video-cleaner.example.com/

# 34. Автообновление сертификата (настройка cron)
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# 35. Проверьте что auto-renewal работает
sudo certbot renew --dry-run

═══════════════════════════════════════════════════════════════════════════════
ЧАСТЬ 6: НАСТРОЙКА ФАЙРВОЛА (UFW)
═══════════════════════════════════════════════════════════════════════════════

# 36. Включите файрвол
sudo ufw enable

# 37. Разрешите SSH (ОЧЕНЬ ВАЖНО!)
sudo ufw allow 22/tcp

# 38. Разрешите HTTP и HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 39. Закройте остальные порты (внутренние сервисы)
# Порты 5000 и 8000 должны быть открыты только для Nginx
sudo ufw status

═══════════════════════════════════════════════════════════════════════════════
ЧАСТЬ 7: ТЕСТИРОВАНИЕ И ВЕРИФИКАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

# 40. Проверьте что сервисы запущены
sudo systemctl status media-cleaner-api
sudo systemctl status media-cleaner-web
sudo systemctl status nginx

# 41. Проверьте что сервисы слушают на портах
sudo netstat -tupln | grep -E '5000|8000'

# 42. Проверьте логи всех сервисов
sudo journalctl -u media-cleaner-api -n 50
sudo journalctl -u media-cleaner-web -n 50
sudo tail -f /var/log/nginx/media-cleaner-error.log

# 43. Тестируйте API напрямую
curl http://127.0.0.1:8000/docs
# Должен вернуть Swagger UI для FastAPI

# 44. Тестируйте через Nginx
curl -I https://video-cleaner.example.com/

# 45. Откройте в браузере (замените домен!)
# https://video-cleaner.example.com

═══════════════════════════════════════════════════════════════════════════════
ЧАСТЬ 8: ОПТИМИЗАЦИЯ И МОНИТОРИНГ
═══════════════════════════════════════════════════════════════════════════════

# 46. Установите Supervisor для управления процессами (опционально)
sudo apt install -y supervisor

# 47. Установите monitoring (опционально)
sudo apt install -y prometheus-node-exporter

# 48. Настройте логирование
sudo mkdir -p /var/log/media-cleaner
sudo chown media_cleaner:media_cleaner /var/log/media-cleaner

# 49. Создайте скрипт резервного копирования
cat > /home/media_cleaner/backup.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/home/media_cleaner/backups"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf $BACKUP_DIR/media_cleaner_$DATE.tar.gz \
    /home/media_cleaner/config.json \
    /home/media_cleaner/logs/
echo "Backup created: $BACKUP_DIR/media_cleaner_$DATE.tar.gz"
EOF

chmod +x /home/media_cleaner/backup.sh

# 50. Добавьте в crontab (резервная копия каждый день в 2 AM)
sudo -u media_cleaner crontab -e
# Добавьте эту строку:
# 0 2 * * * /home/media_cleaner/backup.sh >> /home/media_cleaner/logs/backup.log 2>&1

═══════════════════════════════════════════════════════════════════════════════
ЧАСТЬ 9: КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ ПОСЛЕ УСТАНОВКИ
═══════════════════════════════════════════════════════════════════════════════

# Запустить сервисы
sudo systemctl start media-cleaner-api
sudo systemctl start media-cleaner-web
sudo systemctl start nginx

# Остановить сервисы
sudo systemctl stop media-cleaner-api
sudo systemctl stop media-cleaner-web
sudo systemctl stop nginx

# Перезагрузить сервисы (после изменения кода)
sudo systemctl restart media-cleaner-api
sudo systemctl restart media-cleaner-web
sudo systemctl restart nginx

# Посмотреть реал-тайм логи
sudo journalctl -u media-cleaner-api -f    # API логи
sudo journalctl -u media-cleaner-web -f    # Web логи
sudo tail -f /var/log/nginx/error.log      # Nginx ошибки

# Проверить статус всех сервисов
sudo systemctl status media-cleaner-api media-cleaner-web nginx

# Обновить код (если используете git)
cd /home/media_cleaner
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart media-cleaner-api media-cleaner-web

═══════════════════════════════════════════════════════════════════════════════
ЧАСТЬ 10: РЕШЕНИЕ ПРОБЛЕМ
═══════════════════════════════════════════════════════════════════════════════

# Проблема: "Permission denied" при загрузке файлов
sudo chown -R media_cleaner:media_cleaner /home/media_cleaner/uploads
sudo chmod 755 /home/media_cleaner/uploads

# Проблема: Nginx возвращает 502 Bad Gateway
# Проверьте что сервисы запущены:
sudo systemctl status media-cleaner-api media-cleaner-web
# Посмотрите логи:
sudo journalctl -u media-cleaner-api -n 50

# Проблема: SSL сертификат не работает
# Обновите Nginx конфиг с правильным доменом
# Перегенерируйте сертификат:
sudo certbot renew --force-renewal

# Проблема: FFmpeg не найден
which ffmpeg
# Если не найден: sudo apt install ffmpeg

# Проблема: Высокое использование памяти
# Уменьшите количество workers в systemd сервисе
# Или добавьте swap:
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

═══════════════════════════════════════════════════════════════════════════════
ФИНАЛЬНЫЕ ШАГИ
═══════════════════════════════════════════════════════════════════════════════

1. Замените "video-cleaner.example.com" на ваш реальный домен (3 места!)
2. Замените "admin@example.com" на ваш email
3. Убедитесь что DNS записи указывают на IP сервера
4. Тестируйте в браузере: https://your-domain.com
5. Загрузите тестовое видео
6. Проверьте что обработка работает и нет утечки памяти

═══════════════════════════════════════════════════════════════════════════════
КОМАНДЫ В ОДНУ СТРОКУ (Quick Install)
═══════════════════════════════════════════════════════════════════════════════

# Вся установка за раз (скопируйте и вставьте в терминал):
sudo apt update && sudo apt upgrade -y && \
sudo apt install -y python3.11 python3.11-venv python3-pip build-essential git ffmpeg nginx certbot python3-certbot-nginx && \
sudo useradd -m -s /bin/bash -d /home/media_cleaner media_cleaner && \
cd /home/media_cleaner && \
$(echo 'git clone https://github.com/your-repo/media_cleaner.git . 2>/dev/null || echo "# Используйте SFTP для копирования файлов"') && \
python3.11 -m venv venv && \
source venv/bin/activate && \
pip install --upgrade pip && \
pip install -r requirements.txt && \
mkdir -p uploads logs temp && \
echo "Установка завершена! Проведите части 3-5 для настройки systemd, Nginx и SSL"

═══════════════════════════════════════════════════════════════════════════════
