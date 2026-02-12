#!/usr/bin/env python3
"""Быстрый тест MSE: импортирует VideoProcessor и тестирует один кадр."""

import cv2
import torch
import numpy as np
from pathlib import Path
import os
import sys

def test_mse():
    print("\n" + "="*70)
    print("🔬 ТЕСТ: Проверка улучшения MSE с новыми параметрами")
    print("="*70)
    print(f"epsilon_video: 0.120 (было 0.011)")
    print(f"num_eot_transforms: 4 (было 2)")
    print(f"epsilon_multiplier_strong: 1.8 (новый)")
    
    # Открываем видео
    video_path = "IMG_9864.mp4"
    if not Path(video_path).exists():
        print(f"❌ Видео не найдено: {video_path}")
        return
    
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print(f"❌ Не удалось прочитать видео")
        return
    
    print(f"\n📽️  Размер кадра: {frame.shape[1]}x{frame.shape[0]}")
    
    print("\n🔸 Загрузка ResNet18...")
    
    try:
        # Инициализируем устройство
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"📱 Используется: {device}")
        
        # Импортируем и инициализируем модель
        sys.path.insert(0, str(Path(__file__).parent))
        from media_cleaner import init_device, VideoProcessor
        
        init_device("auto")
        
        # Создаём обработчик видео
        vp = VideoProcessor(epsilon=0.120)
        
        # Применяем шум со множителем 1.8 (strongest)
        print("✓ ResNet18 загружена, применяю шум...")
        
        orig_frame = frame.copy()
        noisy_frame = vp.add_imperceptible_video_noise(frame, strength_mult=1.8)
        
        # Вычисляем различия
        orig_float = orig_frame.astype(np.float32)
        noisy_float = noisy_frame.astype(np.float32)
        
        diff = np.abs(orig_float - noisy_float)
        mse = np.mean(diff ** 2)
        mae = np.mean(diff)
        
        changed_pixels = np.sum(diff > 5)
        total_pixels = diff.shape[0] * diff.shape[1] * diff.shape[2]
        percent_changed = (changed_pixels / total_pixels) * 100
        
        max_diff = np.max(diff)
        
        # Результаты
        print("\n" + "="*70)
        print("📊 РЕЗУЛЬТАТЫ (strength_mult = 1.8x):")
        print("="*70)
        print(f"MSE: {mse:.4f}            {'✅ OK' if mse > 100 else '❌ НУЖНО УВЕЛИЧИТЬ (целевой > 100)'}")
        print(f"MAE: {mae:.4f}")
        print(f"Макс разница: {max_diff:.2f}")
        print(f"Изменённо пикселей: {percent_changed:.4f}%   {'✅ OK' if percent_changed > 15 else '❌ НУЖНО УВЕЛИЧИТЬ (целевой > 15%)'}")
        print("="*70)
        
        if mse > 100 and percent_changed > 15:
            print("\n🎉 УСПЕХ! Adversarial шум теперь достаточно сильный!")
            print("   Видео должно быть защищено от распознавания.")
        else:
            print("\n⚠️  MSE/пиксели недостаточны. Дальнейшие действия:")
            if mse <= 100:
                print("   1. Увеличить epsilon_video в коде media_cleaner.py")
                print("   2. Увеличить epsilon_multiplier_strong (текущий: 1.8)")
                print("   3. Увеличить num_eot_transforms (текущий: 4)")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mse()
