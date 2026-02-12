@echo off
setlocal enabledelayedexpansion

echo.
echo 🚀 ==========================================
echo    Запуск API Сервера Media Cleaner
echo 🚀 ==========================================
echo.

REM Проверка Python
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.8+
    pause
    exit /b 1
)

REM Проверка FFmpeg
ffmpeg -version > nul 2>&1
if errorlevel 1 (
    echo ⚠️  Внимание: FFmpeg не найден!
    echo    Обработка видео может не работать.
    echo.
    pause
)

echo 📦 Установка зависимостей...
pip install -q -r requirements.txt

echo.
echo ✅ ==========================================
echo    API Сервер запускается...
echo ✅ ==========================================
echo.
echo 📡 API Сервер: http://127.0.0.1:8000
echo 🌐 Веб-интерфейс должен быть запущен отдельно!
echo.
echo ⏳ Ожидание... (это может занять несколько секунд)
echo.

timeout /t 2 /nobreak

python media_cleaner.py

pause
