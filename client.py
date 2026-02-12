"""
Клиент для взаимодействия с REST API сервером
Позволяет загружать видео, проверять статус и скачивать результаты
"""

import requests
import json
import argparse
from pathlib import Path
from typing import Optional
import time


class MediaCleanerClient:
    """Клиент для работы с API сервера"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url.rstrip("/")
        self.session = requests.Session()
    
    def upload_video(self, 
                    video_path: str,
                    epsilon: float = 0.120,
                    video_strength: float = 1.0,
                    audio_level: Optional[str] = "слабый",
                    every_n_frames: int = 10,
                    user_id: Optional[str] = None,
                    notes: Optional[str] = None) -> dict:
        """
        Загрузить видео на сервер
        
        Args:
            video_path: Путь к видео-файлу
            epsilon: Сила видео-шума (0.04-0.20)
            video_strength: Множитель силы (1.0-2.0)
            audio_level: Уровень маскировки аудио
            every_n_frames: Применять к каждому N-му кадру
            user_id: ID пользователя
            notes: Заметки
        
        Returns:
            Ответ сервера с task_id
        """
        
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Файл не найден: {video_path}")
        
        print(f"📤 Загрузка видео: {video_path.name}")
        
        with open(video_path, 'rb') as f:
            files = {'file': (video_path.name, f)}
            params = {
                'epsilon': epsilon,
                'video_strength': video_strength,
                'audio_level': audio_level,
                'every_n_frames': every_n_frames,
            }
            
            if user_id:
                params['user_id'] = user_id
            if notes:
                params['notes'] = notes
            
            response = self.session.post(
                f"{self.server_url}/upload",
                files=files,
                params=params
            )
        
        response.raise_for_status()
        result = response.json()
        
        if result['status'] == 'success':
            print(f"✅ Видео загружено успешно!")
            print(f"📌 Task ID: {result['task_id']}")
            print(f"📊 Статус: {result['task']['status_text']}")
        
        return result
    
    def get_task_status(self, task_id: str) -> dict:
        """
        Получить статус задачи
        
        Args:
            task_id: ID задачи
        
        Returns:
            Информация о задаче
        """
        response = self.session.get(f"{self.server_url}/task/{task_id}")
        response.raise_for_status()
        return response.json()['task']
    
    def wait_for_completion(self, task_id: str, check_interval: int = 5, timeout: int = 3600) -> dict:
        """
        Ждать завершения обработки
        
        Args:
            task_id: ID задачи
            check_interval: Интервал проверки в секундах
            timeout: Максимальное время ожидания в секундах
        
        Returns:
            Информация о завершённой задаче
        """
        
        start_time = time.time()
        
        while True:
            task = self.get_task_status(task_id)
            
            elapsed = time.time() - start_time
            elapsed_min = int(elapsed / 60)
            
            if task['status'] == 'completed':
                print(f"\n✅ Задача завершена за {elapsed_min} минут!")
                print(f"📁 Выходной файл: {task['output_video']}")
                return task
            
            elif task['status'] == 'failed':
                print(f"\n❌ Задача завершена с ошибкой!")
                print(f"❌ Ошибка: {task['error_message']}")
                return task
            
            elif task['status'] == 'cancelled':
                print(f"\n🚫 Задача отменена")
                return task
            
            # Показываем прогресс
            print(f"\r⏳ Обработка... {task['progress']:.0f}% | Статус: {task['status_text']} | Прошло: {elapsed_min}м", end='')
            
            if elapsed > timeout:
                print(f"\n⏱️  Таймаут: обработка заняла больше {timeout//60} минут")
                return task
            
            time.sleep(check_interval)
    
    def download_result(self, task_id: str, output_path: Optional[str] = None) -> str:
        """
        Скачать обработанное видео
        
        Args:
            task_id: ID задачи
            output_path: Путь для сохранения (по умолчанию текущая папка)
        
        Returns:
            Путь к скачанному файлу
        """
        
        task = self.get_task_status(task_id)
        
        if task['status'] != 'completed':
            raise Exception(f"Задача не завершена: {task['status']}")
        
        filename = task['output_video']
        if output_path:
            filepath = Path(output_path) / filename
        else:
            filepath = Path(filename)
        
        print(f"📥 Скачивание файла: {filename}")
        
        response = self.session.get(f"{self.server_url}/download/{task_id}", stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                f.write(chunk)
                downloaded += len(chunk)
                
                if total_size:
                    percent = (downloaded / total_size) * 100
                    print(f"\r  {downloaded//(1024*1024)}MB / {total_size//(1024*1024)}MB ({percent:.1f}%)", end='')
        
        print(f"\n✅ Файл сохранён: {filepath}")
        return str(filepath)
    
    def list_tasks(self, user_id: Optional[str] = None, status: Optional[str] = None) -> list:
        """
        Получить список задач
        
        Args:
            user_id: Фильтр по ID пользователя
            status: Фильтр по статусу
        
        Returns:
            Список задач
        """
        params = {}
        if user_id:
            params['user_id'] = user_id
        if status:
            params['status'] = status
        
        response = self.session.get(f"{self.server_url}/tasks", params=params)
        response.raise_for_status()
        return response.json()['tasks']
    
    def cancel_task(self, task_id: str) -> dict:
        """
        Отменить задачу
        
        Args:
            task_id: ID задачи
        
        Returns:
            Результат операции
        """
        response = self.session.post(f"{self.server_url}/cancel/{task_id}")
        response.raise_for_status()
        return response.json()
    
    def get_stats(self) -> dict:
        """Получить статистику сервера"""
        response = self.session.get(f"{self.server_url}/stats")
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> bool:
        """Проверить здоровье сервера"""
        try:
            response = self.session.get(f"{self.server_url}/health")
            response.raise_for_status()
            return response.json()['status'] == 'healthy'
        except:
            return False


def main():
    """Интерфейс командной строки для клиента"""
    
    parser = argparse.ArgumentParser(
        description="Клиент для Media Cleaner Server"
    )
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="URL сервера (по умолчанию: http://localhost:8000)"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Команды')
    
    # Команда upload
    upload_parser = subparsers.add_parser('upload', help='Загрузить видео')
    upload_parser.add_argument('video', help='Путь к видео-файлу')
    upload_parser.add_argument('--epsilon', type=float, default=0.120, help='Сила шума')
    upload_parser.add_argument('--strength', type=float, default=1.0, help='Множитель')
    upload_parser.add_argument('--audio', default='слабый', help='Уровень аудио')
    upload_parser.add_argument('--frames', type=int, default=10, help='Каждый N-й кадр')
    upload_parser.add_argument('--user', help='ID пользователя')
    upload_parser.add_argument('--notes', help='Заметки')
    upload_parser.add_argument('--wait', action='store_true', help='Ждать завершения')
    upload_parser.add_argument('--download', help='Скачать результат в папку')
    
    # Команда status
    status_parser = subparsers.add_parser('status', help='Получить статус задачи')
    status_parser.add_argument('task_id', help='ID задачи')
    status_parser.add_argument('--wait', action='store_true', help='Ждать завершения')
    status_parser.add_argument('--download', help='Скачать результат в папку')
    
    # Команда list
    list_parser = subparsers.add_parser('list', help='Список задач')
    list_parser.add_argument('--user', help='Фильтр по пользователю')
    list_parser.add_argument('--status', help='Фильтр по статусу')
    
    # Команда stats
    subparsers.add_parser('stats', help='Статистика сервера')
    
    # Команда health
    subparsers.add_parser('health', help='Проверить здоровье сервера')
    
    # Команда cancel
    cancel_parser = subparsers.add_parser('cancel', help='Отменить задачу')
    cancel_parser.add_argument('task_id', help='ID задачи')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Создаём клиент
    client = MediaCleanerClient(args.server)
    
    try:
        if args.command == 'upload':
            result = client.upload_video(
                args.video,
                epsilon=args.epsilon,
                video_strength=args.strength,
                audio_level=args.audio,
                every_n_frames=args.frames,
                user_id=args.user,
                notes=args.notes
            )
            
            task_id = result['task_id']
            
            if args.wait:
                task = client.wait_for_completion(task_id)
                if task['status'] == 'completed' and args.download:
                    client.download_result(task_id, args.download)
        
        elif args.command == 'status':
            if args.wait:
                task = client.wait_for_completion(args.task_id)
            else:
                task = client.get_task_status(args.task_id)
            
            print(f"\n📊 Информация о задаче {args.task_id}:")
            print(json.dumps(task, indent=2, ensure_ascii=False))
            
            if task['status'] == 'completed' and args.download:
                client.download_result(args.task_id, args.download)
        
        elif args.command == 'list':
            tasks = client.list_tasks(user_id=args.user, status=args.status)
            
            print(f"\n📋 Найдено задач: {len(tasks)}\n")
            for task in tasks:
                print(f"  ID: {task['task_id']}")
                print(f"  Статус: {task['status_text']}")
                print(f"  Видео: {task['input_video']}")
                print(f"  Прогресс: {task['progress']:.0f}%")
                print()
        
        elif args.command == 'stats':
            stats = client.get_stats()
            print(f"\n📊 Статистика сервера:")
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        elif args.command == 'health':
            if client.health_check():
                print("✅ Сервер здоров")
            else:
                print("❌ Сервер недоступен")
        
        elif args.command == 'cancel':
            result = client.cancel_task(args.task_id)
            print(result['message'])
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
