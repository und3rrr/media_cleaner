@echo off
REM Быстрый запуск программы защиты видео - просто так и всё!

chcp 65001 >nul
setlocal enabledelayedexpansion

".venv\Scripts\python.exe" media_cleaner.py

if errorlevel 1 (
    echo.
    echo ❌ Ошибка! Нажмите любую клавишу для выхода.
    pause >nul
)

exit /b 0
