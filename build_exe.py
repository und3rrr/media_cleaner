#!/usr/bin/env python3
"""
Скрипт для компиляции media_cleaner.py в EXE файл
Требует установленный PyInstaller: pip install pyinstaller

Использование:
  python build_exe.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header(text):
    """Печать заголовка"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def print_success(text):
    """Печать успеха"""
    print(f"✓ {text}")

def print_error(text):
    """Печать ошибки"""
    print(f"✗ {text}")
    sys.exit(1)

def check_pyinstaller():
    """Проверяет наличие PyInstaller"""
    print_header("ПРОВЕРКА PYINSTALLER")
    
    try:
        import PyInstaller
        print_success(f"PyInstaller установлен (версия {PyInstaller.__version__})")
        return True
    except ImportError:
        print_error("""PyInstaller не установлен!
        
Установите его командой:
  pip install pyinstaller
  
Или используйте:
  python -m pip install pyinstaller
""")
        return False

def check_dependencies():
    """Проверяет наличие всех зависимостей"""
    print_header("ПРОВЕРКА ЗАВИСИМОСТЕЙ")
    
    dependencies = {
        'cv2': 'opencv-python',
        'torch': 'torch',
        'torchvision': 'torchvision',
        'PIL': 'Pillow',
        'librosa': 'librosa',
        'soundfile': 'soundfile',
        'numpy': 'numpy',
        'tqdm': 'tqdm'
    }
    
    missing = []
    for module, package in dependencies.items():
        try:
            __import__(module)
            print_success(f"{module} установлен")
        except ImportError:
            print_error(f"{module} НЕ установлен")
            missing.append(package)
    
    if missing:
        print_error(f"""
Отсутствуют следующие пакеты:
  {', '.join(missing)}
  
Установите их командой:
  pip install {' '.join(missing)}
""")
    
    return len(missing) == 0

def build_exe():
    """Собирает EXE файл"""
    print_header("СБОРКА EXE ФАЙЛА")
    
    # Параметры PyInstaller
    main_script = "media_cleaner.py"
    output_dir = "dist"
    build_dir = "build"
    
    # Проверяем наличие скрипта
    if not Path(main_script).exists():
        print_error(f"Файл {main_script} не найден!")
    
    print("Запускаю PyInstaller...")
    print(f"Скрипт: {main_script}")
    print(f"Выходная папка: {output_dir}")
    print()
    
    # Команда для сборки
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # Один файл вместо папки
        "--windowed",                   # Без консольного окна (уберем позже)
        "--icon=NONE",                  # Без иконки
        "--add-data", f"ffmpeg{os.pathsep}ffmpeg",  # Включаем ffmpeg
        "--hidden-import=cv2",          # Скрытый импорт OpenCV
        "--hidden-import=torch",        # Скрытый импорт PyTorch
        "--hidden-import=librosa",      # Скрытый импорт librosa
        "--hidden-import=soundfile",    # Скрытый импорт soundfile
        "--collect-all=torch",          # Собрать все файлы torch
        "--collect-all=torchvision",    # Собрать все файлы torchvision
        "--distpath", output_dir,       # Папка для .exe
        "--buildpath", build_dir,       # Папка для сборки
        "--specpath", ".",              # Папка для .spec файла
        main_script
    ]
    
    # Запускаем PyInstaller
    try:
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print_error(f"PyInstaller завершился с ошибкой (код {result.returncode})")
        
        print_success("EXE файл успешно создан!")
        
        # Найдем созданный файл
        exe_path = Path(output_dir) / f"{Path(main_script).stem}.exe"
        if exe_path.exists():
            file_size = exe_path.stat().st_size / (1024*1024)
            print_success(f"Файл: {exe_path} ({file_size:.1f} MB)")
        
        return True
    
    except Exception as e:
        print_error(f"Ошибка при сборке: {e}")
        return False

def create_launcher_bat():
    """Создает батник для запуска EXE"""
    print_header("СОЗДАНИЕ БАТНИКА")
    
    bat_content = """@echo off
REM Батник для запуска media_cleaner.exe
REM Автор: media_cleaner builder
REM Дата: 2026-01-13

setlocal enabledelayedexpansion

REM Цвет текста
color 0A

REM Получаем папку скрипта
set "SCRIPT_DIR=%~dp0"

REM Переходим в папку со скриптом
cd /d "%SCRIPT_DIR%"

REM Проверяем наличие EXE файла
if not exist "dist\\media_cleaner.exe" (
    echo ============================================================
    echo ✗ ОШИБКА: Файл dist\\media_cleaner.exe не найден!
    echo.
    echo Сначала соберите программу:
    echo   python build_exe.py
    echo ============================================================
    pause
    exit /b 1
)

REM Проверяем наличие ffmpeg
if not exist "ffmpeg\\ffmpeg\\bin\\ffmpeg.exe" (
    echo ============================================================
    echo ✗ ОШИБКА: FFmpeg не найден в папке ffmpeg!
    echo.
    echo Убедитесь что папка ffmpeg находится в проекте.
    echo ============================================================
    pause
    exit /b 1
)

REM Запускаем программу
echo ============================================================
echo Запуск media_cleaner v2.2...
echo ============================================================
echo.

start /wait "media_cleaner" "dist\\media_cleaner.exe"

if errorlevel 1 (
    echo.
    echo ============================================================
    echo ✗ ОШИБКА при запуске программы
    echo ============================================================
    pause
) else (
    echo.
    echo ============================================================
    echo ✓ Программа завершена успешно
    echo ============================================================
)

exit /b 0
"""
    
    bat_file = Path("run_media_cleaner.bat")
    bat_file.write_text(bat_content, encoding='utf-8')
    print_success(f"Батник создан: {bat_file}")

def create_release_package():
    """Создает папку с готовой программой"""
    print_header("ПОДГОТОВКА ПАКЕТА ДЛЯ РАСПРОСТРАНЕНИЯ")
    
    release_dir = Path("media_cleaner_v2.2_standalone")
    
    # Удаляем старую папку если есть
    if release_dir.exists():
        print("Удаляю старую папку...")
        shutil.rmtree(release_dir)
    
    # Создаем новую папку
    release_dir.mkdir(exist_ok=True)
    print_success(f"Создана папка: {release_dir}")
    
    # Копируем EXE файл
    exe_file = Path("dist/media_cleaner.exe")
    if exe_file.exists():
        shutil.copy(exe_file, release_dir / "media_cleaner.exe")
        print_success(f"Скопирован EXE файл")
    
    # Копируем ffmpeg
    ffmpeg_dir = Path("ffmpeg/ffmpeg")
    if ffmpeg_dir.exists():
        shutil.copytree(ffmpeg_dir, release_dir / "ffmpeg")
        print_success(f"Скопирована папка ffmpeg")
    
    # Копируем батник
    bat_file = Path("run_media_cleaner.bat")
    if bat_file.exists():
        shutil.copy(bat_file, release_dir / "run.bat")
        print_success(f"Скопирован батник запуска")
    
    # Копируем инструкции
    user_setup = Path("USER_SETUP_STANDALONE.txt")
    if user_setup.exists():
        shutil.copy(user_setup, release_dir / "README.txt")
        print_success(f"Скопирована инструкция")
    else:
        # Создаем простую инструкцию если нет файла
        readme_content = """╔═══════════════════════════════════════════════════════════════╗
║              MEDIA CLEANER v2.2 - STANDALONE                  ║
║          Защита видео от CV и ASR моделей                   ║
╚═══════════════════════════════════════════════════════════════╝

✅ УСТАНОВКА И ЗАПУСК

Это готовая к использованию версия программы (не требует Python).

ЗАПУСК:
  1. Откройте папку с программой
  2. Дважды кликните на "run.bat"
  3. Выберите видео и параметры обработки

ВСЕ ГОТОВО - просто запустите!

═══════════════════════════════════════════════════════════════

Версия: v2.2 | Дата: 2026-01-13
"""
        (release_dir / "README.txt").write_text(readme_content, encoding='utf-8')
        print_success(f"Создана инструкция")
    
    print_success(f"Пакет готов: {release_dir}")
    
    # Выводим информацию о размере
    total_size = sum(f.stat().st_size for f in release_dir.rglob('*') if f.is_file())
    print_success(f"Общий размер: {total_size / (1024*1024):.1f} MB")

def main():
    """Главная функция"""
    print("""
╔═════════════════════════════════════════════════════════════╗
║         КОМПИЛЯТОР MEDIA_CLEANER В EXE                    ║
║                   Версия v2.2                              ║
╚═════════════════════════════════════════════════════════════╝
""")
    
    # Проверяем PyInstaller
    if not check_pyinstaller():
        sys.exit(1)
    
    # Проверяем зависимости
    if not check_dependencies():
        sys.exit(1)
    
    # Собираем EXE
    if not build_exe():
        sys.exit(1)
    
    # Создаем батник
    create_launcher_bat()
    
    # Создаем пакет для распространения
    create_release_package()
    
    # Финальное резюме
    print_header("СБОРКА ЗАВЕРШЕНА!")
    print("""
✓ EXE файл создан успешно

Файлы готовы:
  • dist/media_cleaner.exe - основная программа
  • run_media_cleaner.bat - батник для запуска
  • media_cleaner_v2.2_standalone/ - пакет для распространения

СЛЕДУЮЩИЙ ШАГ:
  1. Откройте папку media_cleaner_v2.2_standalone
  2. Дважды кликните на run.bat
  3. Программа готова к использованию!

ДЛЯ РАСПРОСТРАНЕНИЯ:
  • Архивируйте папку media_cleaner_v2.2_standalone
  • Отправьте пользователю
  • Пользователь просто распаковывает и кликает на run.bat

═══════════════════════════════════════════════════════════════
""")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
