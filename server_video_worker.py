"""
Обработчик видео для серверной части
Выполняет обработку видео в отдельном потоке
"""

import logging
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Optional
import cv2

from server_config import (
    SERVER_CONFIG, TaskStatus,
    INPUT_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER
)
from queue_processor import processing_queue
from media_cleaner import VideoProcessor, AudioProcessor, extract_audio, assemble_video, cleanup_temps

logger = logging.getLogger("queue_processor")


def process_video_task(task_id: str) -> bool:
    """
    Обрабатывает видео в фоновом потоке
    
    Args:
        task_id: ID задачи из очереди
    
    Returns:
        True если успешно, False иначе
    """
    
    logger.info(f"[START] Processing task: {task_id}")
    processing_queue.update_task(task_id, status=TaskStatus.PROCESSING, started_at=f"{time.time()}")
    
    try:
        task = processing_queue.get_task(task_id)
        if not task:
            raise Exception(f"Task not found: {task_id}")
        
        # Пути файлов
        input_path = INPUT_FOLDER / task.input_video
        base = Path(task.input_video).stem
        temp_folder = str(TEMP_FOLDER / f"{task_id}_{base}_frames")
        temp_audio_orig = str(TEMP_FOLDER / f"{task_id}_{base}_audio_orig.wav")
        temp_audio_adv = str(TEMP_FOLDER / f"{task_id}_{base}_audio_adv.wav")
        output_filename = f"{task_id}_{base}_protected.mp4"
        output_path = OUTPUT_FOLDER / output_filename
        
        logger.info(f"[TASK] Input: {input_path}")
        logger.info(f"[TASK] Params: epsilon={task.epsilon}, strength={task.video_strength}, audio={task.audio_level}")
        
        # ──── ШАГ 1: Проверка входного файла ──────────────────────────────
        if not input_path.exists():
            raise FileNotFoundError(f"Входной файл не найден: {input_path}")
        
        # ──── ШАГ 2: Получение параметров видео ───────────────────────────
        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            raise RuntimeError(f"Не удалось открыть видео: {input_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        if total_frames == 0 or fps == 0:
            raise RuntimeError("Не удалось получить параметры видео")
        
        logger.info(f"[VIDEO] Parameters: {total_frames} frames @ {fps}fps")
        
        # ──── ШАГ 3: Обработка видеокадров ────────────────────────────────
        logger.info("[1/3] Video processing...")
        
        video_processor = VideoProcessor(epsilon=task.epsilon)
        # Использовать параметр every_n_frames из задачи (пользовательский выбор)
        every_n_frames = int(task.every_n_frames) if task.every_n_frames else 1
        every_n_frames = max(1, every_n_frames)
        frames_to_process = (total_frames + every_n_frames - 1) // every_n_frames
        
        logger.info(f"[VIDEO] every_n_frames={every_n_frames}, total_frames={total_frames}, frames_to_process={frames_to_process}")
        
        processing_queue.update_task(task_id, progress=10.0, total_frames=frames_to_process)
        
        # Функция для проверки отмены задачи
        def should_cancel():
            task = processing_queue.get_task(task_id)
            return task and task.status == TaskStatus.CANCELLED
        
        # Обработка видеокадров
        processed_temp_folder, noisy_frames = video_processor.process_video(
            str(input_path),
            start_frame=1,
            end_frame=total_frames,
            every_n_frames=every_n_frames,
            video_strength_mult=task.video_strength,
            should_cancel_fn=should_cancel
        )
        
        logger.info(f"[OK] Processed {noisy_frames} frames")
        processing_queue.update_task(task_id, progress=50.0, processed_frames=noisy_frames)
        
        # Проверить отмену задачи
        task = processing_queue.get_task(task_id)
        if task and task.status == TaskStatus.CANCELLED:
            logger.info(f"[CANCEL] Task cancelled during processing: {task_id}")
            # Очистить временные файлы
            if Path(processed_temp_folder).exists():
                shutil.rmtree(processed_temp_folder)
            processing_queue.update_task(task_id, status=TaskStatus.CANCELLED)
            return False
        
        # ──── ШАГ 4: Обработка аудио ──────────────────────────────────────
        logger.info("[2/3] Audio processing...")
        processing_queue.update_task(task_id, progress=60.0)
        
        try:
            extract_audio(str(input_path), temp_audio_orig)
            
            audio_processor = AudioProcessor()
            if task.audio_level and task.audio_level != "None":
                logger.info(f"[AUDIO] Masking level: {task.audio_level}")
                audio_processor.add_imperceptible_audio_noise(
                    temp_audio_orig, 
                    temp_audio_adv, 
                    task.audio_level
                )
                final_audio = temp_audio_adv
            else:
                logger.info("[AUDIO] Masking disabled (original audio)")
                final_audio = temp_audio_orig
        
        except Exception as e:
            logger.warning(f"[WARN] Audio processing error: {e}")
            # Продолжаем без аудио
            final_audio = temp_audio_orig
        
        processing_queue.update_task(task_id, progress=75.0)
        
        # Проверить отмену задачи перед финальной сборкой
        task = processing_queue.get_task(task_id)
        if task and task.status == TaskStatus.CANCELLED:
            logger.info(f"[CANCEL] Task cancelled before assembly: {task_id}")
            # Очистить временные файлы
            cleanup_temps([processed_temp_folder], [temp_audio_orig, temp_audio_processed])
            processing_queue.update_task(task_id, status=TaskStatus.CANCELLED)
            return False
        
        # ──── ШАГ 5: Сборка финального видео ──────────────────────────────
        logger.info("[3/3] Video assembly...")
        processing_queue.update_task(task_id, progress=85.0)
        
        assemble_video(processed_temp_folder, final_audio, fps, str(output_path), use_gpu=True)
        
        logger.info(f"[OK] Video assembled: {output_path}")
        processing_queue.update_task(task_id, progress=95.0)
        
        # ──── ШАГ 6: Очистка временных файлов ─────────────────────────────
        logger.info("[CLEANUP] Clearing temp files...")
        try:
            cleanup_temps(processed_temp_folder, temp_audio_orig, temp_audio_adv)
            
            # Удаляем входный файл после обработки
            if input_path.exists():
                input_path.unlink()
                logger.info(f"[OK] Input removed: {task.input_video}")
        except Exception as e:
            logger.warning(f"[WARN] Cleanup error: {e}")
        
        # ──── УСПЕХ ────────────────────────────────────────────────────────
        logger.info(f"[DONE] Task completed: {task_id}")
        
        processing_queue.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            output_video=output_filename,
            progress=100.0,
            completed_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return True
    
    except Exception as e:
        # ──── ОШИБКА ──────────────────────────────────────────────────────
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"[ERROR] Processing error {task_id}: {error_msg}")
        
        # Сохраняем ошибку в задаче
        processing_queue.update_task(
            task_id,
            status=TaskStatus.FAILED,
            error_message=error_msg,
            progress=0,
            completed_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # Пытаемся очистить временные файлы
        try:
            task = processing_queue.get_task(task_id)
            if task:
                base = Path(task.input_video).stem
                temp_folder = TEMP_FOLDER / f"{task_id}_{base}_frames"
                if temp_folder.exists():
                    shutil.rmtree(temp_folder)
        except:
            pass
        
        return False


def start_queue_processor(num_workers: int = 1):
    """
    Запускает фоновые потоки для обработки очереди видео
    
    Args:
        num_workers: Количество одновременных обработчиков
    """
    
    logger.info(f"[START] Starting {num_workers} queue workers...")
    
    for worker_id in range(num_workers):
        thread = threading.Thread(
            target=queue_worker_loop,
            args=(worker_id,),
            daemon=True,
            name=f"VideoWorker-{worker_id}"
        )
        thread.start()
        logger.info(f"[OK] Worker started #{worker_id}")


def queue_worker_loop(worker_id: int):
    """
    Основной цикл обработчика очереди
    Непрерывно проверяет наличие задач и обрабатывает их
    """
    
    logger.info(f"Worker-{worker_id}: готов к работе")
    
    while True:
        try:
            # Получаем следующую задачу из очереди
            pending_tasks = processing_queue.get_pending_tasks(limit=1)
            
            if pending_tasks:
                task = pending_tasks[0]
                logger.info(f"Worker-{worker_id}: обработка задачи {task.task_id}")
                process_video_task(task.task_id)
            else:
                # Очередь пуста, ждём
                time.sleep(5)
        
        except Exception as e:
            logger.error(f"Worker-{worker_id}: ошибка в основном цикле: {e}")
            time.sleep(10)


def process_metadata_task(task_id: str) -> bool:
    """
    Удаляет метаданные из видео
    """
    logger.info(f"[START] Metadata strip task: {task_id}")
    processing_queue.update_task(task_id, status=TaskStatus.PROCESSING)
    
    try:
        task = processing_queue.get_task(task_id)
        if not task:
            raise Exception(f"Task not found: {task_id}")
        
        input_path = INPUT_FOLDER / task.input_video
        base = Path(task.input_video).stem
        output_filename = f"{task_id}_{base}_cleaned.mp4"
        output_path = OUTPUT_FOLDER / output_filename
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        logger.info(f"[TASK] Stripping metadata: {input_path}")
        processing_queue.update_task(task_id, progress=20.0)
        
        # FFmpeg command to strip metadata
        import subprocess
        cmd = [
            SERVER_CONFIG["ffmpeg_path"], "-y",
            "-i", str(input_path),
            "-c:v", "copy",  # Copy video without re-encoding
            "-c:a", "copy",  # Copy audio without re-encoding
            "-map_metadata", "-1",  # Remove all metadata
            str(output_path)
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {result.stderr}")
        
        logger.info(f"[OK] Metadata stripped: {output_path}")
        processing_queue.update_task(task_id, progress=90.0)
        
        # Clean up input
        if input_path.exists():
            input_path.unlink()
            logger.info(f"[OK] Input removed: {task.input_video}")
        
        logger.info(f"[DONE] Metadata task completed: {task_id}")
        
        processing_queue.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            output_video=output_filename,
            progress=100.0,
            completed_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return True
    
    except Exception as e:
        logger.error(f"[ERROR] Metadata task failed: {e}")
        processing_queue.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message=str(e)
        )
        return False


def process_compress_task(task_id: str, target_size_mb: int) -> bool:
    """
    Сжимает видео до указанного размера
    """
    logger.info(f"[START] Compress task: {task_id} (target: {target_size_mb}MB)")
    processing_queue.update_task(task_id, status=TaskStatus.PROCESSING)
    
    try:
        import subprocess
        import cv2
        
        task = processing_queue.get_task(task_id)
        if not task:
            raise Exception(f"Task not found: {task_id}")
        
        input_path = INPUT_FOLDER / task.input_video
        base = Path(task.input_video).stem
        output_filename = f"{task_id}_{base}_compressed.mp4"
        output_path = OUTPUT_FOLDER / output_filename
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Get video parameters
        cap = cv2.VideoCapture(str(input_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 1
        cap.release()
        
        logger.info(f"[VIDEO] Source: {total_frames} frames @ {fps}fps, duration: {duration:.1f}s")
        processing_queue.update_task(task_id, progress=10.0)
        
        # Get video resolution to preserve it
        cap = cv2.VideoCapture(str(input_path))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        logger.info(f"[VIDEO] Resolution: {width}x{height}")
        
        # Use CRF-based encoding for high quality with reasonable file size
        # CRF 18-20 = visually lossless / very high quality
        # CRF 21-28 = good quality with smaller file size
        # Calculate CRF based on target size
        
        original_size_mb = input_path.stat().st_size / (1024 * 1024)
        size_ratio = target_size_mb / original_size_mb if original_size_mb > 0 else 0.5
        
        # Higher compression = higher CRF (worse quality)
        if size_ratio > 0.8:
            crf = 18  # Very high quality
        elif size_ratio > 0.6:
            crf = 20  # High quality
        elif size_ratio > 0.4:
            crf = 23  # Good quality
        else:
            crf = 26  # Acceptable quality for aggressive compression
        
        logger.info(f"[COMPRESS] Original: {original_size_mb:.1f}MB, Target: {target_size_mb}MB (ratio: {size_ratio:.1%}), CRF: {crf}")
        processing_queue.update_task(task_id, progress=20.0)
        
        # Use FFmpeg with CRF for high quality encoding
        cmd = [
            SERVER_CONFIG["ffmpeg_path"], "-y",
            "-i", str(input_path),
            "-c:v", "libx264",
            "-crf", str(crf),  # Quality level (lower = better, but larger)
            "-preset", "slow",  # Better compression with good quality
            "-vf", f"scale={width}:{height}",  # Preserve original resolution
            "-c:a", "aac",
            "-b:a", "192k",  # Good audio quality
            str(output_path)
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {result.stderr}")
        
        # Get output file size
        output_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"[OK] Compressed: {output_size_mb:.2f}MB (target was {target_size_mb}MB)")
        processing_queue.update_task(task_id, progress=90.0, output_size_mb=output_size_mb)
        
        # Clean up input
        if input_path.exists():
            input_path.unlink()
            logger.info(f"[OK] Input removed: {task.input_video}")
        
        logger.info(f"[DONE] Compress task completed: {task_id}")
        
        processing_queue.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            output_video=output_filename,
            progress=100.0,
            output_size_mb=output_size_mb,
            completed_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return True
    
    except Exception as e:
        logger.error(f"[ERROR] Compress task failed: {e}")
        processing_queue.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message=str(e)
        )
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Тест обработки видео
    print("Тест обработчика видео...")
    print("Создание тестовой задачи...")
    
    task_id = processing_queue.create_task(
        "test_video.mp4",
        epsilon=0.12,
        user_id="test_user"
    )
    
    print(f"✓ Создана задача: {task_id}")
    print("(В реальности обработка запускается в фоновом потоке из server_app.py)")
