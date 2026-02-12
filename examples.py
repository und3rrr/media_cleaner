"""
Примеры использования Imperceptible Protected Video Generator v2.0

Этот файл содержит примеры прямого вызова функций программы
без интерактивного интерфейса.
"""

from pathlib import Path
import sys

# Добавляем текущую папку в path для импорта
sys.path.insert(0, str(Path(__file__).parent))

from media_cleaner import (
    VideoProcessor, 
    AudioProcessor,
    extract_audio,
    assemble_video,
    cleanup_temps
)
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──── ПРИМЕР 1: Обработка одного видео с минимальными параметрами ────────────
def example_1_basic_protection():
    """
    Пример 1: Базовая защита всего видео
    """
    logger.info("\n" + "="*70)
    logger.info("ПРИМЕР 1: Базовая защита всего видео")
    logger.info("="*70)
    
    input_video = "test_video.mp4"  # Замените на ваше видео
    
    if not Path(input_video).exists():
        logger.error(f"Видео не найдено: {input_video}")
        return
    
    # Создаём обработчики
    video_proc = VideoProcessor(epsilon=0.011, num_eot=2)
    audio_proc = AudioProcessor()
    
    # Обработка видео
    base = Path(input_video).stem
    input_dir = Path(input_video).parent.resolve()
    
    # Обработка видеокадров
    logger.info("Processing video frames...")
    temp_folder, noisy_count = video_proc.process_video(
        input_video,
        start_frame=1,
        end_frame=99999,  # All frames
        every_n_frames=1   # Each frame
    )
    
    logger.info(f"[OK] Processed frames: {noisy_count}")
    
    # Обработка аудио
    logger.info("Обработка аудио...")
    temp_audio_orig = str(input_dir / f"{base}_audio_orig.wav")
    temp_audio_adv = str(input_dir / f"{base}_audio_adv.wav")
    
    extract_audio(input_video, temp_audio_orig)
    audio_proc.add_imperceptible_audio_noise(temp_audio_orig, temp_audio_adv, "слабый")
    
    # Сборка
    logger.info("Сборка финального видео...")
    output_final = str(input_dir / f"{base}_protected_example1.mp4")
    
    # Получаем fps
    import cv2
    cap = cv2.VideoCapture(input_video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    
    assemble_video(temp_folder, temp_audio_adv, fps, output_final)
    
    # Cleanup
    cleanup_temps(temp_folder, temp_audio_orig, temp_audio_adv)
    
    logger.info(f"[OK] Result: {output_final}\n")


# ──── ПРИМЕР 2: Обработка части видео с разными параметрами ─────────────────
def example_2_partial_protection():
    """
    Пример 2: Защита только части видео (кадры 100-600)
    с сильным уровнем маскировки звука
    """
    logger.info("\n" + "="*70)
    logger.info("ПРИМЕР 2: Защита части видео (кадры 100-600)")
    logger.info("="*70)
    
    input_video = "test_video.mp4"  # Замените на ваше видео
    
    if not Path(input_video).exists():
        logger.error(f"Видео не найдено: {input_video}")
        return
    
    # Создаём обработчики
    video_proc = VideoProcessor(epsilon=0.015, num_eot=3)  # Более сильная защита
    audio_proc = AudioProcessor()
    
    # Обработка видео
    base = Path(input_video).stem
    input_dir = Path(input_video).parent.resolve()
    
    logger.info("Processing video frames (frames 100-600, every 5-th)...")
    temp_folder, noisy_count = video_proc.process_video(
        input_video,
        start_frame=100,      # From frame 100
        end_frame=600,        # To frame 600
        every_n_frames=5      # Every 5-th frame (= 20% of range)
    )
    
    logger.info(f"[OK] Processed frames: {noisy_count}")
    
    # Обработка аудио (сильный уровень)
    logger.info("Обработка аудио (уровень: сильный)...")
    temp_audio_orig = str(input_dir / f"{base}_audio_orig.wav")
    temp_audio_adv = str(input_dir / f"{base}_audio_adv.wav")
    
    extract_audio(input_video, temp_audio_orig)
    audio_proc.add_imperceptible_audio_noise(temp_audio_orig, temp_audio_adv, "сильный")
    
    # Сборка
    logger.info("Сборка финального видео...")
    output_final = str(input_dir / f"{base}_protected_example2.mp4")
    
    # Получаем fps
    import cv2
    cap = cv2.VideoCapture(input_video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    
    assemble_video(temp_folder, temp_audio_adv, fps, output_final)
    
    # Cleanup
    cleanup_temps(temp_folder, temp_audio_orig, temp_audio_adv)
    
    logger.info(f"[OK] Result: {output_final}\n")


# ──── ПРИМЕР 3: Обработка только видео (без аудио) ─────────────────────────
def example_3_video_only():
    """
    Пример 3: Защита только видео (без обработки аудио)
    """
    logger.info("\n" + "="*70)
    logger.info("ПРИМЕР 3: Защита только видео")
    logger.info("="*70)
    
    input_video = "test_video.mp4"  # Замените на ваше видео
    
    if not Path(input_video).exists():
        logger.error(f"Видео не найдено: {input_video}")
        return
    
    # Создаём обработчик видео
    video_proc = VideoProcessor(epsilon=0.011, num_eot=2)
    
    # Обработка видео
    base = Path(input_video).stem
    
    logger.info("Processing video frames...")
    temp_folder, noisy_count = video_proc.process_video(
        input_video,
        start_frame=1,
        end_frame=99999,
        every_n_frames=1
    )
    
    logger.info(f"[OK] Processed frames: {noisy_count}")
    
    # Сборка (берём оригинальный звук)
    logger.info("Сборка видео с оригинальным звуком...")
    output_final = f"{base}_protected_video_only.mp4"
    
    # Получаем fps
    import cv2
    cap = cv2.VideoCapture(input_video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    
    assemble_video(temp_folder, input_video, fps, output_final)
    
    # Cleanup
    cleanup_temps(temp_folder)
    
    logger.info(f"[OK] Result: {output_final}\n")


# ──── ПРИМЕР 4: Обработка только аудио ──────────────────────────────────────
def example_4_audio_only():
    """
    Пример 4: Защита только аудио (видео остаётся без изменений)
    """
    logger.info("\n" + "="*70)
    logger.info("ПРИМЕР 4: Защита только аудио")
    logger.info("="*70)
    
    input_video = "test_video.mp4"  # Замените на ваше видео
    
    if not Path(input_video).exists():
        logger.error(f"Видео не найдено: {input_video}")
        return
    
    # Создаём обработчик аудио
    audio_proc = AudioProcessor()
    base = Path(input_video).stem
    input_dir = Path(input_video).parent.resolve()
    
    # Извлечение и обработка аудио
    logger.info("Извлечение аудио...")
    temp_audio_orig = str(input_dir / f"{base}_audio_orig.wav")
    temp_audio_adv = str(input_dir / f"{base}_audio_adv.wav")
    
    extract_audio(input_video, temp_audio_orig)
    
    logger.info("Обработка аудио (уровень: средний)...")
    audio_proc.add_imperceptible_audio_noise(temp_audio_orig, temp_audio_adv, "средний")
    
    # Сборка (используем оригинальные кадры, защищённый звук)
    logger.info("Сборка видео с защищённым звуком...")
    output_final = f"{base}_protected_audio_only.mp4"
    
    # Используем текущую папку как "временную" для оригинальных кадров
    # Проще: используем ffmpeg для замены звука
    import subprocess
    result = subprocess.run([
        r"C:\users\user\desktop\media_cleaner\ffmpeg\ffmpeg\bin\ffmpeg.exe", "-y",
        "-i", input_video,
        "-i", temp_audio_adv,
        "-c:v", "copy",  # Копируем видео без перекодирования
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        output_final
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if result.returncode == 0:
        logger.info(f"[OK] Result: {output_final}")
    else:
        logger.error(f"[ERROR] Audio replacement error: {result.stderr}")
    
    # Очистка
    for tmp in [temp_audio_orig, temp_audio_adv]:
        if Path(tmp).exists():
            Path(tmp).unlink()
    
    logger.info()


# ──── ГЛАВНОЕ МЕНЮ ──────────────────────────────────────────────────────────
def main():
    """Главное меню примеров."""
    print("\n╔" + "="*68 + "╗")
    print("║ Примеры использования Media Cleaner v2.0                         ║")
    print("╚" + "="*68 + "╝\n")
    
    print("Доступные примеры:")
    print("1. Базовая защита всего видео")
    print("2. Защита части видео с сильными параметрами")
    print("3. Защита только видео (без обработки аудио)")
    print("4. Защита только аудио (видео без изменений)")
    print("0. Выход")
    
    choice = input("\nВыберите пример (0-4): ").strip()
    
    if choice == "1":
        example_1_basic_protection()
    elif choice == "2":
        example_2_partial_protection()
    elif choice == "3":
        example_3_video_only()
    elif choice == "4":
        example_4_audio_only()
    elif choice == "0":
        print("До свидания!")
    else:
        print("❌ Неверный выбор")


if __name__ == "__main__":
    main()
