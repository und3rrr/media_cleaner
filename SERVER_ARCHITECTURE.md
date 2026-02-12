# Архитектура серверной части Media Cleaner

## 📋 Структура проекта

```
media_cleaner/
│
├── 🎨 ОСНОВНЫЕ ФАЙЛЫ (исходная версия)
├── media_cleaner.py              # Основной модуль обработки видео
├── requirements.txt              # Зависимости Python
│
├── 🌐 СЕРВЕРНАЯ ЧАСТЬ
├── server_config.py              # Конфигурация сервера
├── server_app.py                 # REST API (FastAPI)
├── server_video_worker.py        # Обработчик видео в фоне
├── queue_processor.py            # Управление очередью задач
├── run_server.py                 # Главный скрипт запуска
├── client.py                     # Python клиент для API
│
├── 📁 ПАПКИ (создаются автоматически)
├── videos_input/                 # Входящие видео
├── videos_output/                # Обработанные видео
├── videos_temp/                  # Временные файлы
├── server_logs/                  # Логи сервера
├── queue_db/                     # База данных задач
│
├── 📚 ДОКУМЕНТАЦИЯ
├── SERVER_DEPLOYMENT.md          # Развертывание на production
├── QUICKSTART_SERVER.md          # Быстрый старт
├── INTEGRATION_EXAMPLES.md       # Примеры интеграции
│
└── 📦 ЗАВИСИМОСТИ
    ├── ffmpeg/                   # FFmpeg для обработки видео
    └── __pycache__/              # Кэш Python
```

## 🏗️ Компоненты архитектуры

### 1. REST API сервер (`server_app.py`)
**FastAPI приложение**
- Эндпоинты для загрузки, проверки статуса, скачивания видео
- Обработка HTTP запросов пользователей
- CORS поддержка для веб приложений
- Auto-документация OpenAPI/Swagger

```
Пользователь → HTTP Request → REST API (FastAPI) → Очередь задач
```

### 2. Очередь обработки (`queue_processor.py`)
**Система управления задачами**
- Хранение информации о задачах (JSON БД)
- Управление статусами (pending → processing → completed/failed)
- Фильтрация и поиск задач
- Уникальные ID задач для каждого видео

Структура задачи:
```json
{
  "task_id": "a1b2c3d4",
  "input_video": "a1b2c3d4_video.mp4",
  "status": "processing",
  "progress": 45.5,
  "epsilon": 0.12,
  "audio_level": "слабый",
  "user_id": "user_001",
  "created_at": "2026-02-11T14:37:00",
  "started_at": "2026-02-11T14:38:00",
  "output_video": null,
  "error_message": null
}
```

### 3. Обработчик видео (`server_video_worker.py`)
**Фоновые потоки для обработки**
- Обработка видеокадров (VideoProcessor)
- Обработка аудио (AudioProcessor)
- Управление временными файлами
- Обработка ошибок и логирование

Жизненный цикл задачи:
```
PENDING → PROCESSING → COMPLETED
                    → FAILED
                    → CANCELLED
```

### 4. Конфигурация (`server_config.py`)
**Централизованные настройки**
- Пути к папкам
- Параметры обработки по умолчанию
- Лимиты (размер видео, одновременные задачи)
- Настройки логирования

## 🔄 Поток работы

```
┌─────────────────────────────────────────────────────────┐
│                      Пользователь                        │
│            (Python клиент, веб, curl)                   │
└──────────────────┬──────────────────────────────────────┘
                   │ POST /upload (видео + параметры)
                   ↓
        ┌──────────────────────┐
        │   REST API сервер    │
        │     (server_app)     │
        └──────────┬───────────┘
                   │ Сохраняет видео в videos_input/
                   │ Создает задачу
                   ↓
        ┌──────────────────────┐
        │  Очередь задач       │
        │ (queue_processor)    │
        └──────────┬───────────┘
                   │ task_id возвращается пользователю
                   ↓
        ┌──────────────────────┐
        │ Фоновые обработчики  │
        │ (server_video_worker)│
        └──────────┬───────────┘
                   │ Обработка видеокадров
                   │ Обработка аудио
                   │ Сборка видео
                   ↓
        ┌──────────────────────┐
        │  videos_output/      │
        │  (обработанное видео)│
        └──────────┬───────────┘
                   │ Пользователь получает результат
                   │ GET /download/{task_id}
                   ↓
┌─────────────────────────────────────────────────────────┐
│                 Пользователь скачивает видео             │
└─────────────────────────────────────────────────────────┘
```

## 📊 База данных задач

Задачи хранятся в файле `queue_db/tasks.json`:

```json
{
  "a1b2c3d4": {
    "task_id": "a1b2c3d4",
    "input_video": "a1b2c3d4_myfile.mp4",
    "status": "completed",
    "created_at": "2026-02-11T14:37:00",
    "started_at": "2026-02-11T14:38:00",
    "completed_at": "2026-02-11T14:42:00",
    "epsilon": 0.12,
    "video_strength": 1.0,
    "audio_level": "слабый",
    "every_n_frames": 10,
    "output_video": "a1b2c3d4_myfile_protected.mp4",
    "error_message": null,
    "progress": 100.0,
    "user_id": "user_001",
    "notes": "Testing parameters"
  },
  "b2c3d4e5": {
    ...
  }
}
```

## 🔐 Безопасность

### Уникализация файлов

Каждому файлу назначается уникальный ID:

```python
task_id = str(uuid.uuid4())[:8]  # Пример: "a1b2c3d4"

# Входной файл
input_file = f"{task_id}_{original_name}.mp4"
# Пример: "a1b2c3d4_video.mp4"

# Выходной файл
output_file = f"{task_id}_{base_name}_protected.mp4"
# Пример: "a1b2c3d4_video_protected.mp4"
```

Это предотвращает:
- ✅ Конфликты при одновременной загрузке видео с одинаковыми именами
- ✅ Доступ к чужим файлам (если добавить проверку user_id)
- ✅ Перезапись файлов

### Изоляция пользователей

Каждый пользователь может отслеживать свои задачи:

```python
# Получить все задачи пользователя
my_tasks = client.list_tasks(user_id="user_001")

# Каждая задача содержит метаинформацию
for task in my_tasks:
    print(f"ID: {task['task_id']}")
    print(f"Статус: {task['status']}")
```

## ⚙️ Параметры обработки

### Видео параметры

| Параметр | Диапазон | По умолчанию | Описание |
|----------|----------|--------------|---------|
| epsilon | 0.04-0.20 | 0.120 | Сила adversarial noise |
| video_strength | 1.0-2.0 | 1.0 | Множитель усиления |
| every_n_frames | 1-30 | 10 | Применять к каждому N-му кадру |

### Аудио параметры

| Уровень | Использование |
|---------|----------------|
| None | Без маскировки (оригинальный звук) |
| "слабый" | Минимальное воздействие (по умолчанию) |
| "средний" | Среднее воздействие |
| "сильный" | Максимальное воздействие |

## 🚀 Масштабируемость

### Одновременные обработки

```python
# server_config.py
SERVER_CONFIG = {
    "max_concurrent_tasks": 3,  # Одновременно 3 видео
}

# run_server.py
python run_server.py --workers 3
```

### Оптимизация

**Для слабых серверов:**
```bash
python run_server.py --workers 1 --port 8000
```

**Для мощных серверов:**
```bash
python run_server.py --workers 8 --port 8000
```

## 📈 Мониторинг и статистика

### Получение статистики

```bash
curl http://localhost:8000/stats
```

Ответ:
```json
{
  "queue": {
    "total": 15,
    "pending": 3,
    "processing": 2,
    "completed": 10,
    "failed": 0
  },
  "config": {
    "max_concurrent_tasks": 3,
    "max_video_size_gb": 2
  }
}
```

### Просмотр логов

```bash
# Основной лог
tail -f server_logs/server.log

# Лог обработки видео
tail -f server_logs/queue.log

# Реальный мониторинг
watch -n 1 'wc -l server_logs/*.log'
```

## 🔧 Расширения и кастомизация

### Добавление нового формата видео

```python
# server_config.py
SERVER_CONFIG = {
    "supported_video_formats": {
        '.mp4', '.mov', '.avi', '.mkv', '.webm',
        '.flv', '.m4v'  # Добавить новые форматы
    }
}
```

### Добавление webhook уведомлений

```python
# server_app.py
@app.post("/upload_with_webhook")
async def upload_with_webhook(
    file: UploadFile,
    webhook_url: str = None,
    ...
):
    # Обработать и отправить результат на webhook
    pass
```

### Добавление аутентификации

```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

@app.post("/upload")
async def upload_video(
    api_key: str = Depends(api_key_header),
    ...
):
    if not validate_api_key(api_key):
        raise HTTPException(status_code=403)
```

## 💾 Резервное копирование

### Резервирование БД задач

```bash
# Ежедневное резервирование
cp queue_db/tasks.json backups/tasks_$(date +%Y%m%d).json

# Восстановление
cp backups/tasks_20260211.json queue_db/tasks.json
```

### Резервирование видео

```bash
# Архивирование завершённых видео
tar -czf archive_$(date +%Y%m%d).tar.gz videos_output/
```

## 📝 Логирование

Логирование настраивается в `server_config.py`:

```python
LOGGING_CONFIG = {
    "handlers": {
        "file": {
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,      # Максимум 5 файлов
        }
    }
}
```

Это позволяет отследить все операции сервера для отладки и аудита.
