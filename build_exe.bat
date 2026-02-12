@echo off
REM Батник для быстрой сборки media_cleaner.exe
REM Автоматически устанавливает PyInstaller и собирает EXE

setlocal enabledelayedexpansion
color 0A

echo ============================================================
echo  КОМПИЛЯТОР MEDIA_CLEANER В EXE
echo  Версия v2.2
echo ============================================================
echo.

REM Получаем папку скрипта
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo [1/4] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ ОШИБКА: Python не установлен или не в PATH!
    echo.
    echo Установите Python с python.org и добавьте в PATH
    pause
    exit /b 1
)
echo ✓ Python найден

echo.
echo [2/4] Установка PyInstaller...
pip install pyinstaller >nul 2>&1
if errorlevel 1 (
    echo ✓ PyInstaller уже установлен (или ошибка, проверьте вручную)
) else (
    echo ✓ PyInstaller установлен
)

echo.
echo [3/4] Проверка зависимостей...
pip install opencv-python torch torchvision pillow librosa soundfile numpy tqdm >nul 2>&1
if errorlevel 1 (
    echo ⚠ Некоторые зависимости могут быть установлены неправильно
    echo   Проверьте консоль выше
) else (
    echo ✓ Все зависимости установлены
)

echo.
echo [4/4] Запуск сборки EXE...
echo.
echo Это может занять 10-30 минут. НЕ закрывайте это окно!
echo.

python build_exe.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo ✗ ОШИБКА при сборке!
    echo ============================================================
    pause
    exit /b 1
) else (
    echo.
    echo ============================================================
    echo ✓ СБОРКА ЗАВЕРШЕНА!
    echo ============================================================
    echo.
    echo Пакет готов: media_cleaner_v2.2_standalone
    echo.
    echo Следующие шаги:
    echo   1. Откройте папку media_cleaner_v2.2_standalone
    echo   2. Дважды кликните на run.bat
    echo   3. Проверьте что программа работает
    echo.
    echo Для распространения:
    echo   1. Архивируйте папку media_cleaner_v2.2_standalone
    echo   2. Отправьте архив пользователю
    echo   3. Пользователь распаковывает и кликает на run.bat
    echo.
    pause
)

exit /b 0
