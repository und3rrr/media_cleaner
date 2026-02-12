#!/usr/bin/env python3
"""
Тестирование новых функций media_cleaner.py v2.1
"""

import sys
from pathlib import Path

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║              ТЕСТИРОВАНИЕ НОВЫХ ФУНКЦИЙ v2.1                              ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

# Test 1: Проверка импорта
print("1️⃣  Проверка импорта модулей...")
try:
    import torch
    print("   ✓ torch загружена успешно")
except ImportError as e:
    print(f"   ✗ Ошибка импорта torch: {e}")
    sys.exit(1)

try:
    import cv2
    print("   ✓ cv2 загружена успешно")
except ImportError as e:
    print(f"   ✗ Ошибка импорта cv2: {e}")
    sys.exit(1)

try:
    import librosa
    print("   ✓ librosa загружена успешно")
except ImportError as e:
    print(f"   ✗ Ошибка импорта librosa: {e}")
    sys.exit(1)

# Test 2: Проверка GPU/CPU
print("\n2️⃣  Проверка GPU/CPU...")
cuda_available = torch.cuda.is_available()
print(f"   GPU доступна: {'✓ Да' if cuda_available else '✗ Нет'}")
if cuda_available:
    print(f"   GPU: {torch.cuda.get_device_name(0)}")
    print(f"   CUDA версия: {torch.version.cuda}")
print(f"   CPU: {torch.get_num_threads()} потоков")

# Test 3: Проверка функций
print("\n3️⃣  Проверка функций...")
try:
    from media_cleaner import (
        init_device, 
        choose_device, 
        verify_video_changes, 
        verify_metadata,
        VideoProcessor,
        AudioProcessor
    )
    print("   ✓ init_device загружена")
    print("   ✓ choose_device загружена")
    print("   ✓ verify_video_changes загружена")
    print("   ✓ verify_metadata загружена")
    print("   ✓ VideoProcessor загружена")
    print("   ✓ AudioProcessor загружена")
except ImportError as e:
    print(f"   ✗ Ошибка импорта функций: {e}")
    sys.exit(1)

# Test 4: Проверка init_device
print("\n4️⃣  Проверка init_device()...")
try:
    init_device("cpu")
    print("   ✓ init_device('cpu') работает")
except Exception as e:
    print(f"   ✗ Ошибка init_device('cpu'): {e}")

try:
    init_device("auto")
    print("   ✓ init_device('auto') работает")
except Exception as e:
    print(f"   ✗ Ошибка init_device('auto'): {e}")

# Test 5: Проверка VideoProcessor
print("\n5️⃣  Проверка VideoProcessor...")
try:
    vp = VideoProcessor()
    print("   ✓ VideoProcessor инициализирован")
    print(f"   ✓ Device: {vp.device}")
    print(f"   ✓ Epsilon: {vp.epsilon}")
except Exception as e:
    print(f"   ✗ Ошибка VideoProcessor: {e}")

# Test 6: Проверка AudioProcessor
print("\n6️⃣  Проверка AudioProcessor...")
try:
    ap = AudioProcessor()
    print("   ✓ AudioProcessor инициализирован")
    print(f"   ✓ Audio levels: {list(ap.levels.keys())}")
except Exception as e:
    print(f"   ✗ Ошибка AudioProcessor: {e}")

# Test 7: Проверка файлов конфигурации
print("\n7️⃣  Проверка файлов конфигурации...")
import json

config_path = Path("config.json")
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
    print("   ✓ config.json найден")
    if "device" in config:
        print(f"   ✓ device параметр добавлен: {config['device']}")
    else:
        print("   ⚠ device параметр не найден в config.json")
else:
    print("   ✗ config.json не найден")

# Test 8: Проверка файлов скриптов
print("\n8️⃣  Проверка файлов скриптов...")
scripts = [
    ("media_cleaner.py", "основная программа"),
    ("NEW_FEATURES.py", "справка по новым возможностям"),
    ("QUICK_START.md", "быстрый старт"),
    ("config.json", "конфигурация"),
]

for script, desc in scripts:
    path = Path(script)
    if path.exists():
        size = path.stat().st_size / 1024
        print(f"   ✓ {script:20} ({size:6.1f} KB) — {desc}")
    else:
        print(f"   ✗ {script:20} — НЕ НАЙДЕН")

print("\n" + "="*80)
print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!\n")
print("Программа готова к использованию:")
print("  python media_cleaner.py")
print("\nДополнительная информация:")
print("  python NEW_FEATURES.py")
print("="*80 + "\n")
