"""
Конфигурация серверной части Imperceptible Protected Video Generator v2.0
"""

import os
from pathlib import Path
from typing import Dict

# ──── ОСНОВНЫЕ ПУТИ ────────────────────────────────────────────────────────
SERVER_ROOT = Path(__file__).parent
INPUT_FOLDER = SERVER_ROOT / "videos_input"
OUTPUT_FOLDER = SERVER_ROOT / "videos_output"
TEMP_FOLDER = SERVER_ROOT / "videos_temp"
LOGS_FOLDER = SERVER_ROOT / "server_logs"
QUEUE_DB_FOLDER = SERVER_ROOT / "queue_db"

# ──── СОЗДАНИЕ ПАПОК ──────────────────────────────────────────────────────
for folder in [INPUT_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER, LOGS_FOLDER, QUEUE_DB_FOLDER]:
    folder.mkdir(parents=True, exist_ok=True)

# ──── КОНФИГУРАЦИЯ СЕРВЕРА ────────────────────────────────────────────────
SERVER_CONFIG = {
    # Пути
    "input_folder": str(INPUT_FOLDER),
    "output_folder": str(OUTPUT_FOLDER),
    "temp_folder": str(TEMP_FOLDER),
    "logs_folder": str(LOGS_FOLDER),
    "queue_db_folder": str(QUEUE_DB_FOLDER),
    
    # REST API
    "host": "127.0.0.1",  # Локальный хост для браузера
    "port": 8000,
    "debug": False,
    
    # Параметры обработки по умолчанию
    "default_video_epsilon": 0.120,
    "default_video_strength": 1.0,
    "default_audio_level": "слабый",  # None, "слабый", "средний", "сильный"
    "default_every_n_frames": 10,
    
    # Лимиты
    "max_video_size_gb": 2,  # Максимальный размер видео в GB
    "max_concurrent_tasks": 3,  # Максимум одновременных обработок
    "task_timeout_hours": 24,  # Таймаут задачи в часах
    
    # Параметры видео
    "supported_video_formats": {'.mp4', '.mov', '.avi', '.mkv', '.webm'},
    "ffmpeg_path": r"C:\users\user\desktop\media_cleaner\ffmpeg\ffmpeg\bin\ffmpeg.exe",
    
    # Очистка
    "auto_cleanup_days": 7,  # Удалять завершённые задачи старше N дней
    "cleanup_schedule_hour": 2,  # Время запуска очистки (2 часа ночи)
}

# ──── КОНФИГУРАЦИЯ ЛОГИРОВАНИЯ ────────────────────────────────────────────
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": str(LOGS_FOLDER / "server.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "queue": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": str(LOGS_FOLDER / "queue.log"),
            "maxBytes": 10485760,
            "backupCount": 3,
        }
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
        "queue_processor": {
            "handlers": ["console", "queue"],
            "level": "DEBUG",
        }
    }
}

# ──── СОСТОЯНИЯ ЗАДАЧ ─────────────────────────────────────────────────────
class TaskStatus:
    """Статусы задач обработки"""
    PENDING = "pending"          # Ожидает обработки
    PROCESSING = "processing"    # Обрабатывается
    COMPLETED = "completed"      # Успешно завершена
    FAILED = "failed"            # Ошибка при обработке
    CANCELLED = "cancelled"      # Отменена пользователем

TASK_STATUSES = {
    TaskStatus.PENDING: "[WAIT] Waiting for processing",
    TaskStatus.PROCESSING: "[PROCESS] Processing",
    TaskStatus.COMPLETED: "[OK] Completed",
    TaskStatus.FAILED: "[ERROR] Error",
    TaskStatus.CANCELLED: "[CANCEL] Cancelled",
}

# ──── ПРОВЕРКА КОНФИГУРАЦИИ ────────────────────────────────────────────────
def validate_config() -> bool:
    """Проверяет корректность конфигурации."""
    errors = []
    
    # Проверка путей
    if not Path(SERVER_CONFIG["ffmpeg_path"]).exists():
        errors.append(f"FFmpeg не найден: {SERVER_CONFIG['ffmpeg_path']}")
    
    # Проверка папок
    for key in ["input_folder", "output_folder", "temp_folder", "logs_folder"]:
        folder = Path(SERVER_CONFIG[key])
        if not folder.exists():
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Не удалось создать папку {key}: {e}")
    
    # Проверка прав доступа на запись
    try:
        test_file = Path(SERVER_CONFIG["logs_folder"]) / ".test"
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        errors.append(f"Нет прав доступа на запись в logs_folder: {e}")
    
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return False
    
    print("[OK] Configuration is valid")
    return True


if __name__ == "__main__":
    print("Проверка конфигурации сервера...")
    validate_config()
    print(f"\n[FOLDERS] Folder structure:")
    print(f"  Input:  {INPUT_FOLDER}")
    print(f"  Output: {OUTPUT_FOLDER}")
    print(f"  Temp:   {TEMP_FOLDER}")
    print(f"  Logs:   {LOGS_FOLDER}")
    print(f"\n🔧 REST API будет доступен по адресу: http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
