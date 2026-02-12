@echo off
REM ═══════════════════════════════════════════════════════════════════════
REM Media Cleaner - Запуск полного сервера (API + Веб интерфейс)
REM ═══════════════════════════════════════════════════════════════════════

echo.
echo  ╔════════════════════════════════════════════════════════════════╗
echo  ║          MEDIA CLEANER - Запуск сервера + интерфейс          ║
echo  ╚════════════════════════════════════════════════════════════════╝
echo.

REM Проверить Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не установлен!
    echo Скачайте Python с https://www.python.org
    pause
    exit /b 1
)

REM Проверить зависимости
echo [1/3] 📦 Проверка зависимостей...
pip install -r requirements.txt

REM Запустить API сервер в фоне
echo.
echo [2/3] 🚀 Запуск API сервера на http://127.0.0.1:8000...
start "API Server" cmd /k python run_server.py

REM Ждать пока сервер запустится
timeout /t 3 /nobreak

REM Запустить Веб интерфейс
echo.
echo [3/3] 🌐 Запуск веб интерфейса на http://127.0.0.1:5000...
timeout /t 2 /nobreak

python -c "import webbrowser; webbrowser.open('http://127.0.0.1:5000')" 2>nul
python web_interface.py

echo.
echo ✅ Сервер запущен!
echo.
echo 🌐 Откройте в браузере: http://127.0.0.1:5000
echo 📡 API доступен на: http://127.0.0.1:8000
echo.
pause
