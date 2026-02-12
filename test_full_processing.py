#!/usr/bin/env python3
"""
Полный тест обработки видео с новыми параметрами adversarial шума.
Пройдёт весь цикл обработки и проверит результаты.
"""

import sys
import subprocess
from pathlib import Path

def main():
    print("\n" + "="*70)
    print("📹 ПОЛНЫЙ ТЕСТ ОБРАБОТКИ ВИДЕО")
    print("="*70)
    print("\nЭтот тест обработает видео IMG_9864.mp4 со следующими параметрами:")
    print("  • epsilon_video: 0.120 (11x увеличение, было 0.011)")
    print("  • num_eot_transforms: 4 (было 2)")
    print("  • strength_multiplier: 1.8 для уровня 'сильный'")
    print("\n⏱️  Время обработки: ~2-5 минут на CPU")
    print("\n" + "="*70)
    
    # Проверяем видео
    video_path = "IMG_9864.mp4"
    if not Path(video_path).exists():
        print(f"❌ Видео не найдено: {video_path}")
        return False
    
    print(f"✅ Видео найдено: {video_path}")
    
    # Подтверждение
    response = input("\n🤔 Хотите начать обработку? (y/n): ").strip().lower()
    if response != 'y':
        print("❌ Отменено пользователем")
        return False
    
    print("\n⏳ Запуск обработки видео...")
    print("="*70 + "\n")
    
    # Запускаем основной скрипт
    try:
        # Используем subprocess для имитации интерактивного ввода
        # Последовательно: выбираем GPU/CPU (опция 3 - auto), затем начало/конец кадров
        
        # Создадим скрипт автоматического ввода
        auto_input = """3
1
-1
сильный
10
y
"""
        
        result = subprocess.run(
            [sys.executable, "media_cleaner.py"],
            input=auto_input,
            text=True,
            capture_output=False,
            timeout=600  # 10 минут максимум
        )
        
        if result.returncode == 0:
            print("\n" + "="*70)
            print("✅ ОБРАБОТКА УСПЕШНО ЗАВЕРШЕНА!")
            print("="*70)
            
            # Проверяем вывод
            protected_path = "IMG_9864_protected.mp4"
            if Path(protected_path).exists():
                size = Path(protected_path).stat().st_size
                print(f"✅ Выходной файл создан: {protected_path}")
                print(f"   Размер: {size / 1024 / 1024:.2f} MB")
                return True
            else:
                print(f"⚠️  Файл не найден: {protected_path}")
                return False
        else:
            print(f"\n❌ Обработка завершилась с ошибкой (код {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Обработка заняла слишком много времени (> 10 минут)")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
