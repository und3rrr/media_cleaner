"""
Главный скрипт для запуска сервера обработки видео
"""

import logging
import logging.config
import argparse
from pathlib import Path
import sys

from server_config import SERVER_CONFIG, LOGGING_CONFIG, validate_config
from server_video_worker import start_queue_processor
from server_app import run_server

# Настройка логирования
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def main():
    """Главная функция запуска сервера"""
    
    parser = argparse.ArgumentParser(
        description="Imperceptible Protected Video Generator - Server"
    )
    parser.add_argument(
        "--host",
        default=SERVER_CONFIG["host"],
        help=f"IP адрес для прослушивания (по умолчанию: {SERVER_CONFIG['host']})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=SERVER_CONFIG["port"],
        help=f"Порт для прослушивания (по умолчанию: {SERVER_CONFIG['port']})"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=SERVER_CONFIG["max_concurrent_tasks"],
        help=f"Количество обработчиков видео (по умолчанию: {SERVER_CONFIG['max_concurrent_tasks']})"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Включить режим отладки"
    )
    
    args = parser.parse_args()
    
    # Проверка конфигурации
    print("\n" + "="*70)
    print("🔧 Imperceptible Protected Video Generator - SERVER v2.0")
    print("="*70)
    
    if not validate_config():
        logger.error("[ERROR] Configuration is not valid. Fix errors before running.")
        sys.exit(1)
    
    # Показываем параметры запуска
    print(f"\n📋 Параметры запуска:")
    print(f"  Host:    {args.host}")
    print(f"  Port:    {args.port}")
    print(f"  Workers: {args.workers}")
    print(f"  Debug:   {args.debug}")
    
    print(f"\n[INFO] Folders:")
    print(f"  Input:   {SERVER_CONFIG['input_folder']}")
    print(f"  Output:  {SERVER_CONFIG['output_folder']}")
    print(f"  Temp:    {SERVER_CONFIG['temp_folder']}")
    print(f"  Logs:    {SERVER_CONFIG['logs_folder']}")
    
    print(f"\n[API] Server will be available at:")
    print(f"  http://{args.host}:{args.port}")
    print(f"  Документация: http://{args.host}:{args.port}/docs")
    
    print("\n" + "="*70 + "\n")
    
    # Запуск обработчика очереди
    logger.info("[START] Starting video processing server...")
    start_queue_processor(num_workers=args.workers)
    
    # Запуск REST API сервера
    try:
        run_server(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("\n🛑 Сервер остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[ERROR] Critical error when starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
