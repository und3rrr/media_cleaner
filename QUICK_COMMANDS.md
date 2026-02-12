# 🚀 Быстрые команды для Media Cleaner Server

## Установка и первый запуск

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Проверить конфигурацию
python server_config.py

# 3. Запустить сервер (откроется на http://localhost:8000)
python run_server.py
```

## REST API через браузер

```
Swagger UI:     http://localhost:8000/docs
ReDoc:          http://localhost:8000/redoc
API endpoint:   http://localhost:8000
```

## Python клиент (рекомендуется)

```bash
# Загрузить и дождаться завершения
python client.py upload video.mp4 --wait --download ./results

# Просто загрузить
python client.py upload video.mp4 --user user_001

# Проверить статус
python client.py status <task_id>

# Ожидание завершения
python client.py status <task_id> --wait --download ./results

# Список задач
python client.py list
python client.py list --user user_001
python client.py list --status completed

# Статистика
python client.py stats

# Проверить здоровье
python client.py health

# Отменить задачу
python client.py cancel <task_id>
```

## curl (любая платформа)

```bash
# Загрузить видео
curl -X POST "http://localhost:8000/upload" \
  -F "file=@video.mp4" \
  -F "epsilon=0.15" \
  -F "audio_level=средний" \
  -F "user_id=user_001"

# Получить статус
curl "http://localhost:8000/task/<task_id>"

# Список задач
curl "http://localhost:8000/tasks?user_id=user_001"

# Скачать видео
curl "http://localhost:8000/download/<task_id>" -o result.mp4

# Отменить задачу
curl -X POST "http://localhost:8000/cancel/<task_id>"

# Статистика
curl "http://localhost:8000/stats"

# Здоровье сервера
curl "http://localhost:8000/health"
```

## Запуск сервера с параметрами

```bash
# Локальное тестирование (1 worker)
python run_server.py --workers 1 --port 8000

# Production (4 workers)
python run_server.py --host 192.168.1.100 --workers 4

# С отладкой
python run_server.py --debug

# На отличающемся порту
python run_server.py --port 8080
```

## Мониторинг логов

```bash
# Основной лог сервера
tail -f server_logs/server.log

# Лог обработки видео
tail -f server_logs/queue.log

# Обе очереди одновременно
tail -f server_logs/*.log

# Только ошибки
grep ERROR server_logs/*.log

# Real-time статистика
watch -n 1 'python client.py stats'
```

## Управление задачами

```bash
# Получить все задачи
python client.py list --limit 100

# Получить незавершённые задачи
python client.py list --status pending

# Получить обрабатываемые задачи
python client.py list --status processing

# Получить завершённые задачи
python client.py list --status completed

# Получить ошибочные задачи
python client.py list --status failed
```

## Администрирование

```bash
# Очистить старые задачи (старше 7 дней)
python client.py cleanup

# Очистить старые задачи (старше N дней)
python client.py cleanup --days 30

# Проверить конфигурацию
python server_config.py

# Просмотреть БД задач
cat queue_db/tasks.json | python -m json.tool
```

## Python скрипты

### Загрузить и дождаться

```python
from client import MediaCleanerClient

client = MediaCleanerClient("http://localhost:8000")

# Загрузить
result = client.upload_video("video.mp4", user_id="user_001")
task_id = result['task_id']

# Дождаться завершения
task = client.wait_for_completion(task_id)

# Скачать
if task['status'] == 'completed':
    client.download_result(task_id, output_path="./results")
```

### Batch обработка (много видео)

```python
from client import MediaCleanerClient
from pathlib import Path

client = MediaCleanerClient("http://localhost:8000")

for video in Path("./videos").glob("*.mp4"):
    result = client.upload_video(str(video), user_id="batch_user")
    print(f"Загружено: {video.name} → {result['task_id']}")

# Дождаться всех задач
tasks = client.list_tasks(user_id="batch_user")
for task in tasks:
    if task['status'] != 'completed':
        task = client.wait_for_completion(task['task_id'])
        if task['status'] == 'completed':
            client.download_result(task['task_id'], "results")
```

### Получить информацию о задаче

```python
from client import MediaCleanerClient

client = MediaCleanerClient("http://localhost:8000")
task = client.get_task_status("<task_id>")

print(f"Статус: {task['status_text']}")
print(f"Прогресс: {task['progress']}%")
print(f"Input: {task['input_video']}")
print(f"Output: {task['output_video']}")
```

## Docker

```bash
# Собрать образ
docker build -t media-cleaner .

# Запустить контейнер
docker run -p 8000:8000 \
  -v $(pwd)/videos_output:/app/videos_output \
  media-cleaner

# Запустить с параметрами
docker run -p 8000:8000 \
  -e WORKERS=4 \
  media-cleaner python run_server.py --workers 4
```

## Linux systemd сервис

```bash
# Показать статус
sudo systemctl status media-cleaner

# Запустить сервис
sudo systemctl start media-cleaner

# Остановить сервис
sudo systemctl stop media-cleaner

# Перезагрузить
sudo systemctl restart media-cleaner

# Просмотреть логи
sudo journalctl -u media-cleaner -f

# Включить автозапуск
sudo systemctl enable media-cleaner
```

## Nginx

```bash
# Проверить конфигурацию
sudo nginx -t

# Перезагрузить Nginx
sudo systemctl reload nginx

# Просмотреть логи
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Отладка

```bash
# Проверить, запущен ли сервер
curl http://localhost:8000/health

# Проверить статистику
curl http://localhost:8000/stats | python -m json.tool

# Список всех задач с информацией
curl http://localhost:8000/tasks?limit=1000 | python -m json.tool

# Информация о конкретной задаче
curl http://localhost:8000/task/<task_id> | python -m json.tool
```

## Часто используемые команды

```bash
# Ежедневная проверка
python client.py health
python client.py stats

# Загрузить видео и дождаться
python client.py upload video.mp4 --wait --download ./results

# Просмотреть логи (последние 50 строк)
tail -50 server_logs/queue.log

# Очистить старые файлы
python client.py cleanup --days 7

# Перезагрузить сервис (Linux)
sudo systemctl restart media-cleaner
```

## Переменные окружения (опционально)

```bash
# Установить переменные перед запуском
export MEDIA_CLEANER_WORKERS=4
export MEDIA_CLEANER_PORT=8000
export MEDIA_CLEANER_DEBUG=false

python run_server.py
```

## Помощь

```bash
# Показать справку по клиенту
python client.py --help

# Показать справку по конкретной команде
python client.py upload --help
python client.py status --help
python client.py list --help

# API документация в браузере
http://localhost:8000/docs
```

## Полезные ссылки в этом проекте

- 📖 [Быстрый старт](QUICKSTART_SERVER.md)
- 📚 [Полная документация](SERVER_README.md)
- 🏗️ [Архитектура](SERVER_ARCHITECTURE.md)
- 🔧 [Развертывание](SERVER_DEPLOYMENT.md)
- 📝 [Примеры интеграции](INTEGRATION_EXAMPLES.md)
- ✅ [Чеклист](DEPLOYMENT_CHECKLIST.md)

---

**Сохраните эту страницу как закладку для быстрого доступа к командам!** 🔖
