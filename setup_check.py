#!/usr/bin/env python3
"""
Quick Start Guide для Imperceptible Protected Video Generator v2.0

Быстрый старт:
1. Поместите видео в эту папку
2. Запустите: python media_cleaner.py
3. Следуйте интерактивным подсказкам
"""

import sys
from pathlib import Path

def check_dependencies():
    """Проверяет наличие всех необходимых зависимостей."""
    required_packages = {
        'cv2': 'opencv-python',
        'torch': 'torch',
        'torchvision': 'torchvision',
        'PIL': 'Pillow',
        'numpy': 'numpy',
        'librosa': 'librosa',
        'soundfile': 'soundfile',
        'tqdm': 'tqdm'
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("❌ Отсутствуют зависимости:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\n✓ Установите их командой:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True

def check_ffmpeg():
    """Проверяет наличие FFmpeg."""
    import subprocess
    try:
        subprocess.run([r"C:\users\user\desktop\media_cleaner\ffmpeg\ffmpeg\bin\ffmpeg.exe", "-version"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        print("❌ FFmpeg не найден по пути:")
        print("   C:\\users\\user\\desktop\\media_cleaner\\ffmpeg\\ffmpeg\\bin\\ffmpeg.exe")
        return False

def main():
    print("╔" + "="*68 + "╗")
    print("║ Imperceptible Protected Video Generator v2.0 — Quick Start         ║")
    print("╚" + "="*68 + "╝\n")
    
    # Проверяем зависимости
    print("[1/3] Проверка зависимостей Python...")
    if not check_dependencies():
        print("\n❌ Не все зависимости установлены. Выход.")
        sys.exit(1)
    print("✓ Все зависимости установлены\n")
    
    # Проверяем FFmpeg
    print("[2/3] Проверка FFmpeg...")
    if not check_ffmpeg():
        print("\n❌ FFmpeg не найден. Выход.")
        sys.exit(1)
    print("✓ FFmpeg доступен\n")
    
    # Проверяем видеофайлы
    print("[3/3] Поиск видеофайлов...")
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    videos = [f for f in Path('.').iterdir() 
              if f.is_file() and f.suffix.lower() in video_extensions]
    
    if not videos:
        print("⚠️  В папке нет видеофайлов. Скопируйте видео в эту папку и попробуйте снова.")
        print(f"\nПоддерживаемые форматы: {', '.join(video_extensions)}\n")
        sys.exit(1)
    
    print(f"✓ Найдено видеофайлов: {len(videos)}\n")
    
    # Всё готово
    print("="*70)
    print("✓ ВСЁ ГОТОВО! Можно запустить программу:")
    print("\n   python media_cleaner.py\n")
    print("="*70)

if __name__ == "__main__":
    main()
