═══════════════════════════════════════════════════════════════════════════════
БЫСТРОЕ РАЗВЕРТЫВАНИЕ В ОДНУ КОМАНДУ
═══════════════════════════════════════════════════════════════════════════════

ВАЖНО: замените эти значения:
- YOUR_DOMAIN = video-cleaner.example.com
- YOUR_EMAIL = admin@example.com
- YOUR_SERVER_IP = IP адрес сервера

═══════════════════════════════════════════════════════════════════════════════
ВАРИАНТ 1: АВТОМАТИЧЕСКИЙ СКРИПТ РАЗВЕРТЫВАНИЯ (РЕКОМЕНДУЕТСЯ)
═══════════════════════════════════════════════════════════════════════════════

# Скопируйте файлы на сервер (выполнить с локальной машины):
scp -r /path/to/media_cleaner/* root@YOUR_SERVER_IP:/home/
cd /tmp && git clone https://github.com/your-repo/media_cleaner.git media_cleaner
scp -r media_cleaner/* root@YOUR_SERVER_IP:/home/media_cleaner/

# Запустите главный скрипт установки на сервере:
ssh root@YOUR_SERVER_IP "bash /home/media_cleaner/deploy.sh video-cleaner.example.com admin@example.com"

# Скрипт сделает всё автоматически! Подождите 5-10 минут.

═══════════════════════════════════════════════════════════════════════════════
ВАРИАНТ 2: ПОШАГОВЫЕ КОМАНДЫ (если скрипт не подходит)
═══════════════════════════════════════════════════════════════════════════════

# 1. Подключиться к серверу
ssh root@YOUR_SERVER_IP

# 2. Обновить систему
sudo apt update && sudo apt upgrade -y && sudo apt autoremove -y

# 3. Установить зависимости (одна команда)
sudo apt install -y python3.11 python3.11-venv python3-pip build-essential git ffmpeg nginx certbot python3-certbot-nginx supervisor htop

# 4. Создать пользователя и папки
sudo useradd -m -s /bin/bash -d /home/media_cleaner media_cleaner && \
mkdir -p /home/media_cleaner/{uploads,logs,temp,backups} && \
sudo chown -R media_cleaner:media_cleaner /home/media_cleaner && \
sudo chmod 755 /home/media_cleaner/{uploads,logs,temp,backups}

# 5. Перейти в папку приложения (предполагается что файлы уже загружены)
cd /home/media_cleaner

# 6. Создать виртуальное окружение и установить зависимости
sudo -u media_cleaner python3.11 -m venv venv && \
sudo -u media_cleaner bash -c 'source venv/bin/activate && pip install --upgrade pip' && \
sudo -u media_cleaner bash -c 'source venv/bin/activate && pip install -r requirements.txt'

# 7. Обновить config.json для Linux (одно прямое слово sed)
sed -i 's|"path": "[^"]*ffmpeg[^"]*"|"path": "/usr/bin/ffmpeg"|g' /home/media_cleaner/config.json

# 8. Создать systemd сервисы (FastAPI + Flask)
sudo tee /etc/systemd/system/media-cleaner-api.service > /dev/null <<EOF
[Unit]
Description=Media Cleaner API (FastAPI)
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
[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/media-cleaner-web.service > /dev/null <<EOF
[Unit]
Description=Media Cleaner Web (Flask)
After=network.target
[Service]
User=media_cleaner
WorkingDirectory=/home/media_cleaner
Environment="PATH=/home/media_cleaner/venv/bin"
ExecStart=/home/media_cleaner/venv/bin/python -m gunicorn --workers 4 --bind 127.0.0.1:5000 --access-logfile /home/media_cleaner/logs/gunicorn_access.log --error-logfile /home/media_cleaner/logs/gunicorn_error.log main:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
[Install]
WantedBy=multi-user.target
EOF

# 9. Запустить systemd сервисы
sudo systemctl daemon-reload && \
sudo systemctl enable media-cleaner-api.service media-cleaner-web.service && \
sudo systemctl start media-cleaner-api.service media-cleaner-web.service

# 10. Создать Nginx конфиг и перезагрузить
sudo tee /etc/nginx/sites-available/media-cleaner > /dev/null <<'NGINXEOF'
upstream api { server 127.0.0.1:8000; }
upstream web { server 127.0.0.1:5000; }
server { listen 80; server_name video-cleaner.example.com; location /.well-known/acme-challenge/ { root /var/www/certbot; } location / { return 301 https://$server_name$request_uri; } }
server { listen 443 ssl http2; server_name video-cleaner.example.com; ssl_certificate /etc/letsencrypt/live/video-cleaner.example.com/fullchain.pem; ssl_certificate_key /etc/letsencrypt/live/video-cleaner.example.com/privkey.pem; ssl_protocols TLSv1.2 TLSv1.3; client_max_body_size 2G; location / { proxy_pass http://web; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto $scheme; proxy_read_timeout 600s; } location /api/ { proxy_pass http://api/; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto $scheme; proxy_read_timeout 600s; } location /static/ { alias /home/media_cleaner/static/; expires 1d; } }
NGINXEOF

sed -i 's|video-cleaner.example.com|YOUR_DOMAIN|g' /etc/nginx/sites-available/media-cleaner && \
sudo ln -sf /etc/nginx/sites-available/media-cleaner /etc/nginx/sites-enabled/ && \
sudo rm -f /etc/nginx/sites-enabled/default && \
sudo nginx -t && \
sudo systemctl restart nginx

# 11. Получить SSL сертификат (замените домен и Email!)
sudo mkdir -p /var/www/certbot && \
sudo certbot certonly --standalone \
    -d video-cleaner.example.com \
    --email admin@example.com \
    --non-interactive \
    --agree-tos \
    --rsa-key-size 4096

# 12. Перезагрузить Nginx с SSL
sudo systemctl reload nginx

# 13. Проверить статус (всё должно быть Active/running)
sudo systemctl status media-cleaner-api media-cleaner-web nginx --no-pager

═══════════════════════════════════════════════════════════════════════════════
ВАРИАНТ 3: СУПЕР БЫСТРО - ВСЁ В ОДНОЙ СТРОКЕ
═══════════════════════════════════════════════════════════════════════════════

# Скопируйте эту ПОЛНУЮ команду и вставьте в терминал сервера:

sudo apt update && sudo apt upgrade -y && sudo apt install -y python3.11 python3.11-venv python3-pip build-essential git ffmpeg nginx certbot python3-certbot-nginx && sudo useradd -m media_cleaner 2>/dev/null; mkdir -p /home/media_cleaner/{uploads,logs,temp} && cd /tmp && git clone https://github.com/your-repo/media_cleaner.git . 2>/dev/null || echo "Загрузите файлы вручную в /home/media_cleaner" && cp -r ./* /home/media_cleaner/ 2>/dev/null; cd /home/media_cleaner && sudo chown -R media_cleaner:media_cleaner . && sudo -u media_cleaner python3.11 -m venv venv && sudo -u media_cleaner bash -c 'source venv/bin/activate && pip install -q --upgrade pip && pip install -q -r requirements.txt' && sed -i 's|*.ffmpeg.*|"path": "/usr/bin/ffmpeg",|g' config.json && echo "✓ Установка завершена! Следуйте Шагам 8-13 выше для Nginx и SSL"

═══════════════════════════════════════════════════════════════════════════════
ВАРИАНТ 4: ДЛЯ ОПЫТНЫХ - БЕЗ NGINX (только тестирование)
═══════════════════════════════════════════════════════════════════════════════

# Если вы хотите быстро протестировать без Nginx:

ssh root@YOUR_SERVER_IP
apt update && apt install -y python3.11 python3.11-venv git ffmpeg
useradd -m media_cleaner 2>/dev/null
cd /home/media_cleaner
git clone https://github.com/your-repo/media_cleaner.git . || scp -r /path/to/files/* ./
sudo -u media_cleaner python3.11 -m venv venv
sudo -u media_cleaner bash -c 'source venv/bin/activate && pip install -r requirements.txt'

# Запустить оба сервера прямо (без systemd):
sudo -u media_cleaner bash -c 'source venv/bin/activate && python -m uvicorn server_app:app --host 0.0.0.0 --port 8000 &'
sudo -u media_cleaner bash -c 'source venv/bin/activate && python main.py'

# Доступ по IP сервера:
# http://YOUR_SERVER_IP:5000     (веб-интерфейс)
# http://YOUR_SERVER_IP:8000/docs (API документация)

# ВАЖНО: Это только для тестирования! Для production используйте Nginx + systemd

═══════════════════════════════════════════════════════════════════════════════
ПРОВЕРКА ПОСЛЕ УСТАНОВКИ
═══════════════════════════════════════════════════════════════════════════════

# Проверьте что всё работает:
sudo systemctl status media-cleaner-api media-cleaner-web nginx
sudo systemctl is-active media-cleaner-api media-cleaner-web nginx

# Проверьте логи:
sudo journalctl -u media-cleaner-api -n 20
sudo journalctl -u media-cleaner-web -n 20

# Проверьте что порты открыты:
sudo ss -tupln | grep -E '5000|8000|80|443'

# Тестируйте в браузере:
curl -I https://YOUR_DOMAIN    # Должна быть 200 и зелёный HTTPS
curl -I http://127.0.0.1:8000/docs   # API swagger

═══════════════════════════════════════════════════════════════════════════════
ЕСЛИ УСТАНОВКА НЕ УДАЛАСЬ - ПОЛНАЯ ПЕРЕУСТАНОВКА
═══════════════════════════════════════════════════════════════════════════════

# Удалить старый виртуальное окружение и переустановить:
cd /home/media_cleaner
sudo -u media_cleaner rm -rf venv
sudo -u media_cleaner python3.11 -m venv venv
sudo -u media_cleaner bash -c 'source venv/bin/activate && pip install --upgrade pip setuptools wheel'
sudo -u media_cleaner bash -c 'source venv/bin/activate && pip install -r requirements.txt'

# Перезагрузить сервисы:
sudo systemctl restart media-cleaner-api media-cleaner-web

# Если всё ещё не работает - посмотрите полные логи:
sudo journalctl -u media-cleaner-api -n 100

═══════════════════════════════════════════════════════════════════════════════
ПОСЛЕ УСПЕШНОЙ УСТАНОВКИ - ОПТИМИЗАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

# Оптимизация производительности:
# Увеличьте workers если много пользователей:
sudo nano /etc/systemd/system/media-cleaner-api.service
# Измените: --workers 4 на --workers 8 (или больше)

# Включить автообновление SSL сертификата:
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Создать cron job для резервной копии:
sudo -u media_cleaner crontab -e
# Добавьте строку:
# 0 2 * * * tar -czf /home/media_cleaner/backups/backup_$(date +\%Y\%m\%d).tar.gz -C /home/media_cleaner config.json logs

# Изменить количество лог файлов которые хранятся:
sudo journalctl --vacuum=size=100M

# Включить swap если мало памяти:
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile

═══════════════════════════════════════════════════════════════════════════════
ВАЖНЫЕ ЗАМЕТКИ
═══════════════════════════════════════════════════════════════════════════════

⚠️ ВСЕ КОМАНДЫ ДОЛЖНЫ БЫТЬ ЗАПУЩЕНЫ НА СЕРВЕРЕ (через SSH)

⚠️ Замените:
   • YOUR_DOMAIN на ваш реальный домен
   • YOUR_EMAIL на ваш реальный email
   • YOUR_SERVER_IP на IP вашего сервера

⚠️ Убедитесь что:
   • DNS запись установлена и распространилась
   • Файлы проекта загружены на сервер
   • У вас есть права администратора (sudo)

⚠️ Установка PyTorch может занять 5-10 минут - не прерывайте!

⚠️ Если ошибка "Port already in use" - остановите конфликтующий сервис:
   sudo systemctl stop apache2

⚠️ Логи для отладки находятся в:
   /var/log/nginx/
   /home/media_cleaner/logs/
   journalctl -u media-cleaner-*

═══════════════════════════════════════════════════════════════════════════════
ДОПОЛНИТЕЛЬНЫЕ ССЫЛКИ И РЕСУРСЫ
═══════════════════════════════════════════════════════════════════════════════

📚 Полная документация развертывания:
   Откройте SERVER_DEPLOYMENT_GUIDE.md

📋 Команды управления:
   Откройте SERVER_COMMANDS_REFERENCE.md

✅ Чек-лист перед развертыванием:
   Откройте PRE_DEPLOYMENT_CHECKLIST.md

🐛 Если нужна помощь с отладкой:
   1. Посмотрите логи: sudo journalctl -u media-cleaner-api -f
   2. Проверьте конфиг: cat /home/media_cleaner/config.json
   3. Убедитесь что FFmpeg установлен: which ffmpeg

═══════════════════════════════════════════════════════════════════════════════
