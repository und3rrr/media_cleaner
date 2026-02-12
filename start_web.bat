@echo off
setlocal enabledelayedexpansion

echo.
echo 🚀 ==========================================
echo    Запуск Media Cleaner Web Interface
echo 🚀 ==========================================
echo.

REM Проверка Python
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.8+
    pause
    exit /b 1
)

echo 📦 Установка зависимостей...
pip install -q -r requirements.txt

echo.
echo ✅ ==========================================
echo    Веб-интерфейс запускается...
echo ✅ ==========================================
echo.
echo 🌐 Flask:  http://127.0.0.1:5000
echo 📡 API:    http://127.0.0.1:8000
echo.
echo 💡 ВАЖНО: Откройте ВТОРое окно cmd и запустите:
echo.
echo    python media_cleaner.py
echo.
echo ⏳ Ожидание... (это может занять несколько секунд)
echo.

timeout /t 2 /nobreak

python web_interface.py

pause
