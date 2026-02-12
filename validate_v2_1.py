#!/usr/bin/env python3
"""
Финальная валидация всех улучшений v2.1
"""

import sys
from pathlib import Path
import torch
import cv2
import numpy as np

def validate_config():
    """Проверяет конфигурацию в коде"""
    print("="*70)
    print("🔍 ВАЛИДАЦИЯ КОНФИГУРАЦИИ v2.1")
    print("="*70)
    
    from media_cleaner import CONFIG
    
    checks = []
    
    # Проверка epsilon
    if CONFIG["epsilon_video"] >= 0.10:
        print("✅ epsilon_video >= 0.10 (текущий: {})".format(CONFIG["epsilon_video"]))
        checks.append(True)
    else:
        print("❌ epsilon_video слишком низкий (текущий: {})".format(CONFIG["epsilon_video"]))
        checks.append(False)
    
    # Проверка epsilon_multiplier_strong
    if CONFIG.get("epsilon_multiplier_strong", 0) >= 1.5:
        print("✅ epsilon_multiplier_strong >= 1.5 (текущий: {})".format(
            CONFIG.get("epsilon_multiplier_strong")))
        checks.append(True)
    else:
        print("❌ epsilon_multiplier_strong слишком низкий")
        checks.append(False)
    
    # Проверка num_eot_transforms
    if CONFIG["num_eot_transforms"] >= 4:
        print("✅ num_eot_transforms >= 4 (текущий: {})".format(CONFIG["num_eot_transforms"]))
        checks.append(True)
    else:
        print("❌ num_eot_transforms < 4")
        checks.append(False)
    
    return all(checks)

def validate_functions():
    """Проверяет что функции правильно подписаны"""
    print("\n" + "="*70)
    print("🔍 ВАЛИДАЦИЯ ФУНКЦИЙ")
    print("="*70)
    
    from media_cleaner import VideoProcessor, choose_settings
    import inspect
    
    checks = []
    
    # Проверка add_imperceptible_video_noise
    sig = inspect.signature(VideoProcessor.add_imperceptible_video_noise)
    params = list(sig.parameters.keys())
    if 'strength_mult' in params:
        print("✅ add_imperceptible_video_noise имеет параметр strength_mult")
        checks.append(True)
    else:
        print("❌ add_imperceptible_video_noise не имеет параметр strength_mult")
        print("   Параметры: {}".format(params))
        checks.append(False)
    
    # Проверка process_video
    sig = inspect.signature(VideoProcessor.process_video)
    params = list(sig.parameters.keys())
    if 'video_strength_mult' in params:
        print("✅ process_video имеет параметр video_strength_mult")
        checks.append(True)
    else:
        print("❌ process_video не имеет параметр video_strength_mult")
        print("   Параметры: {}".format(params))
        checks.append(False)
    
    return all(checks)

def test_mse():
    """Быстрый тест MSE"""
    print("\n" + "="*70)
    print("🔍 БЫСТРЫЙ ТЕСТ MSE")
    print("="*70)
    
    from media_cleaner import init_device, VideoProcessor
    
    video_path = "IMG_9864.mp4"
    if not Path(video_path).exists():
        print(f"⚠️  Видео не найдено: {video_path} - пропуск теста MSE")
        return True
    
    init_device("auto")
    
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("⚠️  Не удалось прочитать видео - пропуск теста MSE")
        return True
    
    vp = VideoProcessor()
    
    orig_frame = frame.copy()
    noisy_frame = vp.add_imperceptible_video_noise(frame, strength_mult=1.8)
    
    diff = np.abs(orig_frame.astype(np.float32) - noisy_frame.astype(np.float32))
    mse = np.mean(diff ** 2)
    percent_changed = (np.sum(diff > 5) / (diff.shape[0] * diff.shape[1] * diff.shape[2])) * 100
    
    success = mse > 100 and percent_changed > 15
    
    if success:
        print(f"✅ MSE = {mse:.2f} (> 100 требуется)")
        print(f"✅ Пиксели = {percent_changed:.2f}% (> 15% требуется)")
    else:
        print(f"❌ MSE = {mse:.2f} (требуется > 100)")
        print(f"❌ Пиксели = {percent_changed:.2f}% (требуется > 15%)")
    
    return success

def main():
    print("\n" + "="*70)
    print("🎯 ФИНАЛЬНАЯ ВАЛИДАЦИЯ v2.1")
    print("="*70)
    
    all_pass = True
    
    try:
        # Валидация конфига
        if not validate_config():
            all_pass = False
    except Exception as e:
        print(f"❌ Ошибка валидации конфига: {e}")
        all_pass = False
    
    try:
        # Валидация функций
        if not validate_functions():
            all_pass = False
    except Exception as e:
        print(f"❌ Ошибка валидации функций: {e}")
        import traceback
        traceback.print_exc()
        all_pass = False
    
    try:
        # Тест MSE
        if not test_mse():
            all_pass = False
    except Exception as e:
        print(f"❌ Ошибка при тесте MSE: {e}")
        import traceback
        traceback.print_exc()
        all_pass = False
    
    # Итоги
    print("\n" + "="*70)
    if all_pass:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! v2.1 ГОТОВА К ИСПОЛЬЗОВАНИЮ")
        print("="*70)
        print("\nСледующий шаг: python media_cleaner.py")
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        print("="*70)
    
    return all_pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
