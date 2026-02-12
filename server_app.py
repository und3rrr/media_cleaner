"""
REST API сервер для Imperceptible Protected Video Generator
Использует FastAPI + Uvicorn
"""

import logging
import logging.config
import os
import threading
from pathlib import Path
from typing import Optional, Dict
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from server_config import (
    SERVER_CONFIG, LOGGING_CONFIG, 
    INPUT_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER,
    TaskStatus, TASK_STATUSES
)
from queue_processor import processing_queue, ProcessingTask
from server_video_worker import process_video_task

# ──── НАСТРОЙКА ЛОГИРОВАНИЯ ──────────────────────────────────────────────────
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# ──── ИНИЦИАЛИЗАЦИЯ FASTAPI И LIFESPAN ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # ─────── STARTUP (при запуске) ──────────
    logger.info("[API] Starting REST API server...")
    logger.info(f"[API] Input folder: {INPUT_FOLDER}")
    logger.info(f"[API] Output folder: {OUTPUT_FOLDER}")
    logger.info(f"[API] Temp folder: {TEMP_FOLDER}")
    
    stats = processing_queue.get_statistics()
    logger.info(f"[API] Loaded tasks from DB: {stats['total']}")
    logger.info(f"[API] Pending processing: {stats['pending']}")
    
    yield
    
    # ─────── SHUTDOWN (при остановке) ──────────
    logger.info("[API] Shutting down REST API server...")
    processing_queue.save_tasks()


app = FastAPI(
    title="Imperceptible Protected Video Generator API",
    description="REST API для добавления невидимого шума в видео",
    version="2.0",
    lifespan=lifespan
)

# ──── CORS (разрешить запросы с других доменов) ─────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──── МАРШРУТЫ API ───────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Информация о сервисе"""
    stats = processing_queue.get_statistics()
    return {
        "name": "Imperceptible Protected Video Generator API",
        "version": "2.0",
        "status": "running",
        "queue_stats": stats,
        "endpoints": {
            "upload": "/upload",
            "task_status": "/task/{task_id}",
            "task_list": "/tasks",
            "download": "/download/{task_id}",
            "cancel": "/cancel/{task_id}",
            "health": "/health"
        }
    }


@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    epsilon: float = Query(SERVER_CONFIG["default_video_epsilon"]),
    video_strength: float = Query(SERVER_CONFIG["default_video_strength"]),
    audio_level: Optional[str] = Query(SERVER_CONFIG["default_audio_level"]),
    every_n_frames: int = Query(SERVER_CONFIG["default_every_n_frames"]),
    user_id: Optional[str] = Query(None),
    notes: Optional[str] = Query(None),
):
    """
    Загрузить видео для обработки
    
    **Parameters:**
    - **file**: Видео-файл (mp4, mov, avi, mkv, webm)
    - **epsilon**: Сила видео-шума (0.04-0.20), по умолчанию 0.12
    - **video_strength**: Множитель силы (1.0-2.0), по умолчанию 1.0
    - **audio_level**: Уровень аудио маскировки (None/"слабый"/"средний"/"сильный")
    - **every_n_frames**: Применять к каждому N-му кадру (1-30)
    - **user_id**: ID пользователя (опционально)
    - **notes**: Заметки (опционально)
    
    **Returns:** task_id и информация о задаче
    """
    
    try:
        # Проверка расширения файла
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in SERVER_CONFIG["supported_video_formats"]:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый формат: {file_ext}. Поддерживаемые: {SERVER_CONFIG['supported_video_formats']}"
            )
        
        # Проверка размера файла
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell() / (1024**3)  # В GB
        file.file.seek(0)
        
        if file_size > SERVER_CONFIG["max_video_size_gb"]:
            raise HTTPException(
                status_code=413,
                detail=f"Файл слишком большой: {file_size:.2f}GB, максимум {SERVER_CONFIG['max_video_size_gb']}GB"
            )
        
        # Проверка количества одновременных обработок
        processing_tasks = processing_queue.get_all_tasks(TaskStatus.PROCESSING)
        if len(processing_tasks) >= SERVER_CONFIG["max_concurrent_tasks"]:
            raise HTTPException(
                status_code=429,
                detail=f"Сервер занят. Идёт обработка {len(processing_tasks)} видео. Попробуйте позже."
            )
        
        # Сохранение файла с уникальным именем
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        file_path = Path(file.filename)
        unique_filename = f"{unique_id}_{file_path.stem}{file_path.suffix}"
        input_path = INPUT_FOLDER / unique_filename
        
        # Сохраняем файл
        content = await file.read()
        with open(input_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"[UPLOAD] Video uploaded: {unique_filename} ({file_size:.2f}GB)")
        
        # Создание задачи в очереди
        task_id = processing_queue.create_task(
            input_video=unique_filename,
            epsilon=epsilon,
            video_strength=video_strength,
            audio_level=audio_level,
            every_n_frames=every_n_frames,
            user_id=user_id,
            notes=notes,
        )
        
        # Запуск обработки в фоновом потоке
        threading.Thread(target=process_video_task, args=(task_id,), daemon=True).start()
        
        task = processing_queue.get_task(task_id)
        return {
            "status": "success",
            "task_id": task_id,
            "message": "Видео загружено и добавлено в очередь",
            "task": task.to_public_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Load error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Получить статус задачи по ID
    
    **Returns:** Информация о задаче и её статус
    """
    task = processing_queue.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Задача не найдена: {task_id}")
    
    return {
        "status": "success",
        "task": task.to_public_dict()
    }


@app.get("/tasks")
async def list_tasks(
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50),
):
    """
    Получить список задач
    
    **Parameters:**
    - **user_id**: Фильтр по ID пользователя
    - **status**: Фильтр по статусу (pending/processing/completed/failed)
    - **limit**: Максимум задач в ответе
    
    **Returns:** Список задач
    """
    
    if user_id:
        tasks = processing_queue.get_user_tasks(user_id)
    elif status:
        tasks = processing_queue.get_all_tasks(status=status)
    else:
        tasks = processing_queue.get_all_tasks()
    
    # Сортируем по времени создания (новые первыми)
    tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)[:limit]
    
    return {
        "status": "success",
        "count": len(tasks),
        "tasks": [task.to_public_dict() for task in tasks]
    }


@app.get("/download/{task_id}")
async def download_result(task_id: str):
    """
    Скачать обработанное видео
    
    **Returns:** Видео-файл или ошибка
    """
    task = processing_queue.get_task(task_id)
    logger.info(f"[DOWNLOAD] task_id={task_id}, task_found={task is not None}")
    
    if not task:
        logger.error(f"[DL-ERR] Задача не найдена: {task_id}")
        raise HTTPException(status_code=404, detail=f"Задача не найдена: {task_id}")
    
    logger.info(f"[DOWNLOAD] Task status: {task.status}, is_completed: {task.status == TaskStatus.COMPLETED}")
    
    if task.status != TaskStatus.COMPLETED:
        logger.error(f"[DL-ERR] Задача не готова: stats={task.status}")
        raise HTTPException(
            status_code=400,
            detail=f"Видео ещё не готово. Статус: {task.status}"
        )
    
    logger.info(f"[DOWNLOAD] output_video: {task.output_video}, is_set: {bool(task.output_video)}")
    
    if not task.output_video:
        logger.error(f"[DL-ERR] output_video не установлен для task {task_id}")
        raise HTTPException(status_code=404, detail="Выходной файл не найден")
    
    output_path = OUTPUT_FOLDER / task.output_video
    logger.info(f"[DOWNLOAD] Проверка файла: {output_path}, exists: {output_path.exists()}")
    
    if not output_path.exists():
        logger.error(f"[DL-ERR] Файл не найден: {output_path}")
        raise HTTPException(status_code=404, detail=f"Файл был удалён: {output_path}")
    
    logger.info(f"📥 Скачан файл: {task.output_video} (задача {task_id})")
    
    return FileResponse(
        output_path,
        filename=task.output_video,
        media_type="video/mp4"
    )


@app.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """
    Отменить задачу обработки
    
    **Returns:** Статус операции
    """
    success = processing_queue.cancel_task(task_id)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"Не удалось отменить задачу: {task_id}")
    
    return {
        "status": "success",
        "message": f"Задача {task_id} отменена"
    }


@app.get("/stats")
async def get_statistics():
    """
    Получить статистику сервера
    
    **Returns:** Информация о очереди и статистика
    """
    stats = processing_queue.get_statistics()
    
    return {
        "status": "success",
        "queue": stats,
        "config": {
            "max_concurrent_tasks": SERVER_CONFIG["max_concurrent_tasks"],
            "max_video_size_gb": SERVER_CONFIG["max_video_size_gb"],
        }
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервера"""
    stats = processing_queue.get_statistics()
    
    return {
        "status": "healthy",
        "timestamp": Path(__file__).stat().st_mtime,
        "queue_size": stats["total"],
        "processing": stats["processing"]
    }


@app.post("/cleanup")
async def cleanup_old_tasks(days: int = Query(SERVER_CONFIG["auto_cleanup_days"])):
    """
    Удалить старые завершённые задачи
    
    **Parameters:**
    - **days**: Удалить задачи старше N дней
    
    **Returns:** Количество удалённых задач
    """
    count = processing_queue.cleanup_old_tasks(days)
    
    return {
        "status": "success",
        "deleted_tasks": count,
        "message": f"Удалено {count} старых задач"
    }


# ──── УДАЛЕНИЕ МЕТАДАННЫХ ─────────────────────────────────────────────────
@app.post("/strip-metadata")
async def strip_metadata_endpoint(file: UploadFile = File(...)):
    """
    Удалить метаданные из видео
    
    **Parameters:**
    - **file**: Видео-файл
    
    **Returns:** Task ID
    """
    try:
        # Создаём уникальное имя файла
        unique_filename = f"{uuid4()}_{file.filename}"
        input_path = INPUT_FOLDER / unique_filename
        
        # Сохраняем файл
        content = await file.read()
        with open(input_path, 'wb') as f:
            f.write(content)
        
        file_size = len(content) / (1024 ** 3)
        logger.info(f"[UPLOAD] Video uploaded: {unique_filename} ({file_size:.2f}GB)")
        
        # Создание задачи в очереди (специальный тип - metadata)
        task_id = processing_queue.create_task(
            input_video=unique_filename,
            epsilon=0,  # Не используется
            video_strength=1.0,
            audio_level="None",
            every_n_frames=1,
            user_id="web_metadata",
            notes="strip_metadata"
        )
        
        logger.info(f"[OK] Metadata strip task created: {task_id}")
        
        # Запускаем обработку в фоне
        from server_video_worker import process_metadata_task
        threading.Thread(target=process_metadata_task, args=(task_id,), daemon=True).start()
        
        return {
            'status': 'success',
            'task_id': task_id,
            'message': 'Задача добавлена в очередь'
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Strip metadata error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──── СЖАТИЕ ВИДЕО ────────────────────────────────────────────────────────
@app.post("/compress-video")
async def compress_video_endpoint(file: UploadFile = File(...), target_size_mb: int = Query(50)):
    """
    Сжать видео до указанного размера
    
    **Parameters:**
    - **file**: Видео-файл
    - **target_size_mb**: Целевой размер в MB
    
    **Returns:** Task ID
    """
    try:
        if target_size_mb < 5 or target_size_mb > 500:
            raise HTTPException(status_code=400, detail="Размер должен быть от 5 до 500 MB")
        
        # Создаём уникальное имя файла
        unique_filename = f"{uuid4()}_{file.filename}"
        input_path = INPUT_FOLDER / unique_filename
        
        # Сохраняем файл
        content = await file.read()
        with open(input_path, 'wb') as f:
            f.write(content)
        
        file_size = len(content) / (1024 ** 3)
        logger.info(f"[UPLOAD] Video uploaded for compression: {unique_filename} ({file_size:.2f}GB)")
        
        # Создание задачи в очереди (специальный тип - compress)
        task_id = processing_queue.create_task(
            input_video=unique_filename,
            epsilon=0,  # Не используется
            video_strength=1.0,
            audio_level="None",
            every_n_frames=1,
            user_id="web_compress",
            notes=f"compress_to_{target_size_mb}mb"
        )
        
        logger.info(f"[OK] Compress task created: {task_id} (target: {target_size_mb}MB)")
        
        # Запускаем обработку в фоне
        from server_video_worker import process_compress_task
        threading.Thread(
            target=process_compress_task, 
            args=(task_id, target_size_mb), 
            daemon=True
        ).start()
        
        return {
            'status': 'success',
            'task_id': task_id,
            'target_size_mb': target_size_mb,
            'message': 'Задача сжатия добавлена в очередь'
        }
    
    except Exception as e:
        logger.error(f"[ERROR] Compress video error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──── ОБРАБОТЧИК ОШИБОК ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик ошибок"""
    logger.error(f"[ERROR] Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "detail": str(exc)}
    )


# ──── LIFESPAN ОБРАБОТЧИКИ ПЕРЕМЕЩЕНЫ ВЫШЕ ──────────────────────────────────


# ──── ЗАПУСК СЕРВЕРА ─────────────────────────────────────────────────────────
def run_server(host: str = None, port: int = None, debug: bool = False):
    """Запуск REST API сервера"""
    host = host or SERVER_CONFIG["host"]
    port = port or SERVER_CONFIG["port"]
    
    print(f"[START] Server starting at: http://{host}:{port}")
    print(f"[START] API docs available at: http://{host}:{port}/docs")
    
    uvicorn.run(
        "server_app:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )


if __name__ == "__main__":
    # Можно запустить так: python server_app.py
    run_server(debug=False)
