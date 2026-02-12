# 🐧 Debian сервер - Полная установка с веб-интерфейсом

## Шаг 1: Подготовка системы

```bash
# Обновить систему
sudo apt update && sudo apt upgrade -y

# Установить зависимости
sudo apt install -y python3 python3-pip python3-venv git curl
sudo apt install -y ffmpeg libopencv-dev libsm6 libxext6
```

## Шаг 2: Скачать проект Media Cleaner

```bash
# Выбрать папку для установки
cd /opt
sudo mkdir -p media_cleaner
sudo chown $USER:$USER media_cleaner
cd media_cleaner

# Скачать файлы (или скопировать через scp)
git clone <your-repo> .
# или
# scp -r user@local-machine:/path/to/media_cleaner/* .
```

## Шаг 3: Создать виртуальное окружение

```bash
cd /opt/media_cleaner

# Создать venv
python3 -m venv venv

# Активировать
source venv/bin/activate

# Обновить pip
pip install --upgrade pip setuptools wheel
```

## Шаг 4: Установить зависимости Python

```bash
# Установить все пакеты из requirements.txt
pip install -r requirements.txt

# Это включает:
# - torch, torchvision, torchaudio (для GPU обработки)
# - opencv, librosa, soundfile (для видео)
# - fastapi, uvicorn (для API сервера)
# - flask, flask-cors (для веб интерфейса)
```

## Шаг 5: Конфигурация

Обновить **server_config.py** для Linux:

```python
# Путь к FFmpeg (в Linux обычно /usr/bin/ffmpeg)
"ffmpeg_path": "/usr/bin/ffmpeg",

# Папки для обработки
"base_output_dir": "/var/media_cleaner/output",
"queue_file": "/var/media_cleaner/queue.json",
"uploads_dir": "/var/media_cleaner/uploads",
```

Создать папки:

```bash
sudo mkdir -p /var/media_cleaner/{output,uploads}
sudo chown $USER:$USER /var/media_cleaner
chmod 755 /var/media_cleaner
```

## Шаг 6: Тест локально

```bash
cd /opt/media_cleaner
source venv/bin/activate

# Открыть 3 терминала и в каждом выполнить:

# Терминал 1 - API сервер
python run_server.py
# Слушает на http://127.0.0.1:8000

# Терминал 2 - Веб интерфейс
python web_interface.py
# Слушает на http://127.0.0.1:5000

# Терминал 3 - Тест
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:5000/
```

## Шаг 7: Systemd сервисы для запуска при загрузке

### Сервис API (Порт 8000)

```bash
sudo nano /etc/systemd/system/media-cleaner-api.service
```

Содержимое:

```ini
[Unit]
Description=Media Cleaner API Server
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/media_cleaner
Environment="PATH=/opt/media_cleaner/venv/bin"
ExecStart=/opt/media_cleaner/venv/bin/python /opt/media_cleaner/run_server.py
Restart=on-failure
RestartSec=10
StandardOutput=append:/var/log/media-cleaner-api.log
StandardError=append:/var/log/media-cleaner-api.log

[Install]
WantedBy=multi-user.target
```

### Сервис Веб интерфейса (Порт 5000)

```bash
sudo nano /etc/systemd/system/media-cleaner-web.service
```

Содержимое:

```ini
[Unit]
Description=Media Cleaner Web Interface
After=network.target media-cleaner-api.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/media_cleaner
Environment="PATH=/opt/media_cleaner/venv/bin"
Environment="API_SERVER=http://127.0.0.1:8000"
ExecStart=/opt/media_cleaner/venv/bin/python /opt/media_cleaner/web_interface.py 0.0.0.0 5000
Restart=on-failure
RestartSec=10
StandardOutput=append:/var/log/media-cleaner-web.log
StandardError=append:/var/log/media-cleaner-web.log

[Install]
WantedBy=multi-user.target
```

Где `YOUR_USERNAME` - ваше имя пользователя. Получить:

```bash
whoami
```

### Активировать сервисы

```bash
# Перезагрузить systemd
sudo systemctl daemon-reload

# Включить автозапуск
sudo systemctl enable media-cleaner-api.service
sudo systemctl enable media-cleaner-web.service

# Запустить сейчас
sudo systemctl start media-cleaner-api.service
sudo systemctl start media-cleaner-web.service

# Проверить статус
sudo systemctl status media-cleaner-api.service
sudo systemctl status media-cleaner-web.service

# Смотреть логи
sudo journalctl -u media-cleaner-api.service -f
sudo journalctl -u media-cleaner-web.service -f
```

## Шаг 8: Nginx reverse proxy (опционально)

Если хотите получить доступ с домена:

```bash
sudo apt install -y nginx
```

Создать конфиг:

```bash
sudo nano /etc/nginx/sites-available/media-cleaner
```

Содержимое:

```nginx
upstream media_cleaner_api {
    server 127.0.0.1:8000;
}

upstream media_cleaner_web {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 2G;  # Макс размер загрузки
    
    # Веб интерфейс
    location / {
        proxy_pass http://media_cleaner_web;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API сервер
    location /api {
        proxy_pass http://media_cleaner_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;  # Важно для потоковой отправки файлов
        proxy_request_buffering off;
    }
}
```

Активировать:

```bash
sudo ln -s /etc/nginx/sites-available/media-cleaner /etc/nginx/sites-enabled/
sudo nginx -t  # Проверить конфиг
sudo systemctl restart nginx
```

## Шаг 9: SSL сертификат (Let's Encrypt)

Если используется domain:

```bash
sudo apt install -y certbot python3-certbot-nginx

sudo certbot --nginx -d your-domain.com
```

## Шаг 10: Проверка доступности

### Локально
```bash
curl http://127.0.0.1:5000/  # Веб интерфейс
curl http://127.0.0.1:8000/health  # API
```

### Удаленно (если доступен домен)
```bash
curl http://your-domain.com/  # Веб интерфейс
curl http://your-domain.com/api/stats  # API (через /api prefix)
```

### Из браузера
```
http://your-server-ip:5000/
http://your-domain.com/
```

## Шаг 11: Мониторинг и логи

### Просмотр логов

```bash
# Логи API сервера
sudo tail -f /var/log/media-cleaner-api.log

# Логи Веб интерфейса
sudo tail -f /var/log/media-cleaner-web.log

# Логи systemd
sudo journalctl -u media-cleaner-api.service -f
sudo journalctl -u media-cleaner-web.service -f
```

### Перезагрузка сервисов

```bash
# Перезагрузить оба
sudo systemctl restart media-cleaner-api.service media-cleaner-web.service

# Или один
sudo systemctl restart media-cleaner-api.service
```

### Остановка

```bash
sudo systemctl stop media-cleaner-api.service media-cleaner-web.service
```

## Шаг 12: Оптимизация для GPU (опционально)

Если есть NVIDIA GPU:

```bash
# Установить CUDA
sudo apt install -y nvidia-driver-XXX
sudo apt install -y cuda-toolkit

# Проверить
python
>>> import torch
>>> torch.cuda.is_available()
True
>>> torch.cuda.get_device_name(0)
'NVIDIA GeForce RTX 3090'
```

## Примеры команд для администратора

```bash
# Проверить статус обоих сервисов
sudo systemctl status media-cleaner-{api,web}.service

# Перезагрузить оба сразу
sudo systemctl restart media-cleaner-{api,web}.service

# Остановить оба
sudo systemctl stop media-cleaner-{api,web}.service

# Включить автозапуск обоих
sudo systemctl enable media-cleaner-{api,web}.service

# Отключить автозапуск обоих
sudo systemctl disable media-cleaner-{api,web}.service

# Просмотреть последние 50 строк логов API
sudo tail -50 /var/log/media-cleaner-api.log

# Просмотреть все логи за сегодня
sudo grep "$(date +%Y-%m-%d)" /var/log/media-cleaner-api.log

# Полная переустановка зависимостей
cd /opt/media_cleaner
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## Проблемы и решения

### Проблема: "Permission denied" при запуске

```bash
# Решение: дать правильные права доступа
sudo chown -R $USER:$USER /opt/media_cleaner
sudo chown -R $USER:$USER /var/media_cleaner
chmod 755 /opt/media_cleaner
chmod 755 /var/media_cleaner
```

### Проблема: "Port already in use"

```bash
# Найти процесс на порте 5000
sudo lsof -i :5000

# Найти процесс на порте 8000
sudo lsof -i :8000

# Убить процесс (осторожно!)
sudo kill -9 PID
```

### Проблема: "CUDA out of memory"

```bash
# Уменьшить every_n_frames в параметрах
# Или перезагрузить системd сервис
sudo systemctl restart media-cleaner-api.service
```

### Проблема: Медленная обработка

```bash
# Проверить использование CPU/GPU
nvidia-smi          # если есть GPU
top                 # CPU использование

# Уменьшить количество рабочих потоков в server_config.py
"num_workers": 1  # вместо 2-4
```

## Финальная проверка

```bash
# Убедиться, что оба сервиса запущены
sudo systemctl is-active media-cleaner-api.service
sudo systemctl is-active media-cleaner-web.service

# Проверить доступность портов
netstat -tulpn | grep -E ':(5000|8000)'

# Тест API
curl -X GET http://127.0.0.1:8000/health

# Тест Веб интерфейса
curl -X GET http://127.0.0.1:5000/ | head -20
```

## Готово! 🎉

Ваш Media Cleaner сервер с веб-интерфейсом готов работать на Debian!

### Доступ:
- **Веб интерфейс:** http://your-server-ip:5000 или http://your-domain.com
- **API:** http://your-server-ip:8000 или http://your-domain.com/api
- **Логи API:** `sudo tail -f /var/log/media-cleaner-api.log`
- **Логи Web:** `sudo tail -f /var/log/media-cleaner-web.log`

### Удаленная загрузка видео через API:

```bash
curl -X POST \
  -F "file=@video.mp4" \
  -F "epsilon=0.12" \
  -F "audio_level=слабый" \
  http://your-server-ip:5000/upload
```

---

**Версия:** 2.2  
**Дата:** Февраль 2024
