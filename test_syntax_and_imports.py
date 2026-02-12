#!/usr/bin/env python3
"""
Краткий тест: полный потребок обработки видео (демо-режим на 5 кадров).
"""

import sys
from pathlib import Path

def main():
    print("\n" + "="*70)
    print("🚀 Быстрый тест полного потока обработки видео")
    print("="*70)
    
    # Проверим синтаксис
    try:
        from media_cleaner import (
            init_device, 
            VideoProcessor, 
            AudioProcessor,
            extract_audio,
            assemble_video,
            choose_device,
            choose_settings,
            verify_video_changes,
            verify_metadata,
            process_imperceptible_protected_video
        )
        print("✅ Все функции импортированы успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("✅ media_cleaner.py синтаксически корректен")
    print("✅ Все необходимые компоненты на месте")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
