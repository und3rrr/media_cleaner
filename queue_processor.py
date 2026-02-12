"""
Система управления очередью обработки видео
"""

import json
import logging
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum
import threading
import time
from dataclasses import dataclass, asdict

from server_config import (
    SERVER_CONFIG, QUEUE_DB_FOLDER, TaskStatus, 
    TASK_STATUSES, INPUT_FOLDER, OUTPUT_FOLDER
)

logger = logging.getLogger("queue_processor")

# ──── КЛАСС ДЛЯ ХРАНЕНИЯ ИНФОРМАЦИИ О ЗАДАЧЕ ───────────────────────────────
@dataclass
class ProcessingTask:
    """Информация о задаче обработки видео"""
    task_id: str                           # Уникальный ID задачи
    input_video: str                       # Имя входящего видео
    status: str                            # Статус обработки
    created_at: str                        # Время создания
    started_at: Optional[str] = None       # Время начала обработки
    completed_at: Optional[str] = None     # Время завершения
    
    # Параметры обработки
    epsilon: float = 0.120
    video_strength: float = 1.0
    audio_level: Optional[str] = "слабый"
    every_n_frames: int = 10
    
    # Результаты
    output_video: Optional[str] = None     # Имя выходного видео
    output_size_mb: Optional[float] = None # Размер выходного видео (для сжатия)
    error_message: Optional[str] = None    # Сообщение об ошибке
    progress: float = 0.0                  # Прогресс обработки (0-100)
    
    # Информация о кадрах
    processed_frames: int = 0              # Обработано кадров
    total_frames: int = 0                  # Всего кадров
    
    # Метаинформация
    user_id: Optional[str] = None          # ID пользователя (опционально)
    notes: Optional[str] = None            # Заметки пользователя
    
    def to_dict(self) -> Dict:
        """Преобразует задачу в словарь для JSON сериализации"""
        return asdict(self)
    
    def to_public_dict(self) -> Dict:
        """Возвращает публичную информацию о задаче (для API)"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "status_text": TASK_STATUSES.get(self.status, "Неизвестно"),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
            "processed_frames": self.processed_frames,
            "total_frames": self.total_frames,
            "input_video": self.input_video,
            "output_video": self.output_video,
            "error_message": self.error_message,
            "epsilon": self.epsilon,
            "video_strength": self.video_strength,
            "audio_level": self.audio_level,
            "every_n_frames": self.every_n_frames,
            "user_id": self.user_id,
        }


# ──── ОЧЕРЕДЬ ОБРАБОТКИ ─────────────────────────────────────────────────────
class VideoProcessingQueue:
    """Управление очередью видео для обработки"""
    
    def __init__(self):
        self.tasks_db = QUEUE_DB_FOLDER / "tasks.json"
        self.lock = threading.Lock()
        self.tasks: Dict[str, ProcessingTask] = {}
        self.load_tasks()
    
    def load_tasks(self) -> None:
        """Загружает задачи из базы данных"""
        if self.tasks_db.exists():
            try:
                with open(self.tasks_db, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_id, task_data in data.items():
                        self.tasks[task_id] = ProcessingTask(**task_data)
                logger.info(f"Загружено {len(self.tasks)} задач из базы")
            except Exception as e:
                logger.error(f"Ошибка загрузки задач: {e}")
    
    def save_tasks(self) -> None:
        """Сохраняет задачи в базу данных"""
        try:
            with self.lock:
                data = {task_id: task.to_dict() for task_id, task in self.tasks.items()}
                with open(self.tasks_db, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения задач: {e}")
    
    def create_task(self, input_video: str, 
                   epsilon: float = None,
                   video_strength: float = None,
                   audio_level: str = None,
                   every_n_frames: int = None,
                   user_id: str = None,
                   notes: str = None) -> str:
        """
        Создает новую задачу обработки видео.
        Возвращает task_id
        """
        task_id = str(uuid.uuid4())[:8]  # Первые 8 символов UUID
        
        task = ProcessingTask(
            task_id=task_id,
            input_video=input_video,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
            epsilon=epsilon or SERVER_CONFIG["default_video_epsilon"],
            video_strength=video_strength or SERVER_CONFIG["default_video_strength"],
            audio_level=audio_level or SERVER_CONFIG["default_audio_level"],
            every_n_frames=every_n_frames or SERVER_CONFIG["default_every_n_frames"],
            user_id=user_id,
            notes=notes,
        )
        
        with self.lock:
            self.tasks[task_id] = task
        
        self.save_tasks()
        logger.info(f"[OK] Task created: {task_id} (video: {input_video})")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[ProcessingTask]:
        """Получает задачу по ID"""
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """Обновляет поля задачи"""
        if task_id not in self.tasks:
            return False
        
        with self.lock:
            task = self.tasks[task_id]
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            self.tasks[task_id] = task
        
        self.save_tasks()
        return True
    
    def get_pending_tasks(self, limit: int = 1) -> List[ProcessingTask]:
        """Получает ожидающие обработки задачи"""
        pending = [
            task for task in self.tasks.values()
            if task.status == TaskStatus.PENDING
        ]
        return pending[:limit]
    
    def get_user_tasks(self, user_id: str) -> List[ProcessingTask]:
        """Получает все задачи пользователя"""
        return [
            task for task in self.tasks.values()
            if task.user_id == user_id
        ]
    
    def get_all_tasks(self, status: str = None) -> List[ProcessingTask]:
        """Получает все задачи, опционально фильтруя по статусу"""
        if status:
            return [task for task in self.tasks.values() if task.status == status]
        return list(self.tasks.values())
    
    def cancel_task(self, task_id: str) -> bool:
        """Отменяет задачу (даже если уже обрабатывается)"""
        task = self.get_task(task_id)
        logger.debug(f"[DEBUG] Trying to cancel task {task_id}, current status: {task.status if task else 'NOT_FOUND'}")
        
        if not task:
            logger.error(f"[ERROR] Task not found: {task_id}")
            return False
        
        # Разрешить отмену на любом этапе (кроме уже завершивших)
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            logger.warning(f"[WARN] Cannot cancel task {task_id}: already finished (status={task.status})")
            return False
        
        # Отменяем задачу независимо от статуса (PENDING или PROCESSING)
        logger.info(f"[CANCEL] Marking task {task_id} as cancelled")
        self.update_task(task_id, status=TaskStatus.CANCELLED)
        logger.info(f"[OK] Task cancelled: {task_id}")
        return True
    
    def cleanup_old_tasks(self, days: int = None) -> int:
        """
        Удаляет завершённые задачи старше N дней.
        Возвращает количество удалённых задач.
        """
        days = days or SERVER_CONFIG["auto_cleanup_days"]
        cutoff_date = datetime.now() - timedelta(days=days)
        
        to_delete = []
        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task_date = datetime.fromisoformat(task.completed_at)
                if task_date < cutoff_date:
                    to_delete.append(task_id)
        
        with self.lock:
            for task_id in to_delete:
                del self.tasks[task_id]
        
        self.save_tasks()
        logger.info(f"[OK] Deleted {len(to_delete)} old tasks")
        return len(to_delete)
    
    def get_statistics(self) -> Dict:
        """Возвращает статистику очереди"""
        total = len(self.tasks)
        pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
        processing = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING)
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
        
        return {
            "total": total,
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed,
        }


# ──── ГЛОБАЛЬНАЯ ОЧЕРЕДЬ ────────────────────────────────────────────────────
# Создается один раз при импорте модуля
processing_queue = VideoProcessingQueue()


if __name__ == "__main__":
    # Тест функциональности
    logging.basicConfig(level=logging.DEBUG)
    
    print("Тест системы управления очередью...")
    
    # Создание задач
    task1 = processing_queue.create_task(
        "video1.mp4",
        epsilon=0.15,
        user_id="user_001",
        notes="Высокое качество"
    )
    
    task2 = processing_queue.create_task(
        "video2.mp4",
        audio_level="сильный"
    )
    
    print(f"\n✓ Создано 2 задачи: {task1}, {task2}")
    
    # Получение задач
    pending = processing_queue.get_pending_tasks()
    print(f"\n⏳ Ожидающих задач: {len(pending)}")
    for task in pending:
        print(f"  - {task.task_id}: {task.input_video}")
    
    # Обновление статуса
    processing_queue.update_task(task1, status=TaskStatus.PROCESSING, progress=50.0)
    task = processing_queue.get_task(task1)
    print(f"\n✓ Обновлена задача {task1}: {task.status} ({task.progress}%)")
    
    # Статистика
    stats = processing_queue.get_statistics()
    print(f"\n📊 Статистика очереди:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
