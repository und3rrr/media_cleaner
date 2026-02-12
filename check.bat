@echo off
REM Проверка что система готова к работе

chcp 65001 >nul
setlocal enabledelayedexpansion

cls
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo    ✅ ПРОВЕРКА СИСТЕМЫ v2.1
echo ════════════════════════════════════════════════════════════════════════════
echo.

REM Проверяем Python
echo [1/3] Проверяем Python...
where python >nul 2>nul
if errorlevel 1 (
    echo    ❌ Python не найден
    goto error
) else (
    echo    ✅ Python найден
)

REM Проверяем виртуальное окружение
echo [2/3] Проверяем виртуальное окружение...
if not exist ".venv\Scripts\python.exe" (
    echo    ❌ Виртуальное окружение не найдено
    goto error
) else (
    echo    ✅ Виртуальное окружение готово
)

REM Запускаем валидацию
echo [3/3] Проверяем конфигурацию программы...
echo.

".venv\Scripts\python.exe" validate_v2_1.py

if errorlevel 1 (
    goto error
) else (
    goto success
)

:error
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo    ❌ ОШИБКА! Система не готова
echo ════════════════════════════════════════════════════════════════════════════
echo.
echo  Что делать:
echo    1. Убедитесь что Python 3.8+ установлен
echo    2. Откройте PowerShell в этой папке
echo    3. Выполните: python -m venv .venv
echo    4. Выполните: .venv\Scripts\pip install -r requirements.txt
echo    5. Запустите check.bat снова
echo.
pause
exit /b 1

:success
echo.
echo ════════════════════════════════════════════════════════════════════════════
echo    ✅ УСПЕХ! Система готова к работе
echo ════════════════════════════════════════════════════════════════════════════
echo.
echo  Запустите: run.bat  (для меню)
echo  Или:       run_fast.bat  (для быстрого старта)
echo.
pause
exit /b 0
