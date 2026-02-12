#!/usr/bin/env python3
"""Быстрый тест: проверяет улучшение MSE после изменения epsilon."""

import cv2
import torch
import numpy as np
from pathlib import Path
import json
import sys

# Загружаем конфиг
with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

sys.path.insert(0, str(Path(__file__).parent))
from media_cleaner import VideoProcessor, init_device

def test_mse_improvement():
    """Тестирует силу adversarial шума на одном кадре."""
    print("\n" + "="*70)
    print("🔬 ТЕСТ: Проверка MSE и силы adversarial шума")
    print("="*70)
    
    # Инициализируем GPU/CPU
    init_device("auto")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"📱 Устройство: {device}")
    print(f"📊 Параметры:")
    print(f"   epsilon_video: {CONFIG['epsilon_video']}")
    print(f"   num_eot_transforms: {CONFIG['num_eot_transforms']}")
    print(f"   epsilon_multiplier_strong: {CONFIG.get('epsilon_multiplier_strong', 'N/A')}")
    
    # Открываем видео
    video_path = "IMG_9864.mp4"
    if not Path(video_path).exists():
        print(f"❌ Видео не найдено: {video_path}")
        return False
    
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print(f"❌ Не удалось прочитать кадр из {video_path}")
        return False
    
    print(f"📽️  Кадр размер: {frame.shape[1]}x{frame.shape[0]}")
    
    # Создаём обработчик видео
    vp = VideoProcessor(epsilon=CONFIG["epsilon_video"])
    
    # Тестируем разные уровни strength_mult
    strength_levels = {
        "очень слабый (0.6x)": 0.6,
        "слабый (1.0x)": 1.0,
        "средний (1.4x)": 1.4,
        "сильный (1.8x)": 1.8,
    }
    
    results = []
    
    for level_name, strength_mult in strength_levels.items():
        print(f"\n🔸 {level_name}")
        
        try:
            # Применяем шум
            noisy_frame = vp.add_imperceptible_video_noise(frame, strength_mult)
            
            # Вычисляем метрики
            orig_float = frame.astype(np.float32)
            noisy_float = noisy_frame.astype(np.float32)
            
            diff = np.abs(orig_float - noisy_float)
            mse = np.mean(diff ** 2)
            mae = np.mean(diff)
            
            # Процент изменённых пикселей (порог > 5)
            changed_pixels = np.sum(diff > 5)
            total_pixels = diff.shape[0] * diff.shape[1] * diff.shape[2]
            percent_changed = (changed_pixels / total_pixels) * 100
            
            print(f"   MSE: {mse:.2f} {'✅ OK' if mse > 100 else '❌ LOW'}")
            print(f"   MAE: {mae:.2f}")
            print(f"   Изменённо пикселей: {percent_changed:.2f}% {'✅ OK' if percent_changed > 15 else '❌ LOW'}")
            print(f"   Макс разница: {np.max(diff):.2f}")
            
            results.append({
                'level': level_name,
                'strength_mult': strength_mult,
                'mse': mse,
                'mae': mae,
                'percent_changed': percent_changed,
                'max_diff': float(np.max(diff))
            })
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    # Итоговый отчёт
    print("\n" + "="*70)
    print("📈 ИТОГИ:")
    print("="*70)
    
    any_good = False
    for r in results:
        mse_ok = r['mse'] > 100
        pct_ok = r['percent_changed'] > 15
        status = "✅" if (mse_ok and pct_ok) else "⚠️"
        print(f"{status} {r['level']:30s} MSE={r['mse']:7.2f} ({pct_ok and mse_ok and '✓' or '✗'}) Пиксели={r['percent_changed']:5.2f}%")
        if mse_ok and pct_ok:
            any_good = True
    
    print("="*70)
    if any_good:
        print("✅ УСПЕХ! Adversarial шум теперь достаточно сильный")
    else:
        print("⚠️  Внимание: даже при 1.8x множителе MSE < 100")
        print("   Возможные решения:")
        print("   1. Увеличить epsilon_video в config.json ещё больше (текущий: {})".format(CONFIG['epsilon_video']))
        print("   2. Увеличить num_eot_transforms (текущий: {})".format(CONFIG['num_eot_transforms']))
        print("   3. Пересмотреть loss функцию в add_imperceptible_video_noise()")
    
    return any_good

if __name__ == "__main__":
    success = test_mse_improvement()
    sys.exit(0 if success else 1)
