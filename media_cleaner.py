"""
Imperceptible Protected Video Generator v2.0

Программа для добавления "невидимого" шума в видео:
- Шум на кадрах (adversarial noise) — для CV-моделей
- Шум на звуке (audio masking) — для ASR-моделей

Человек почти ничего не замечает, а нейросети сильно путаются.
"""

import logging
import sys
import json
from pathlib import Path
from typing import Optional, Tuple, Dict
import traceback

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torch import nn
from torchvision import models, transforms
from torchvision.models.resnet import ResNet18_Weights
from PIL import Image
import subprocess
import shutil
import librosa
import soundfile as sf
from tqdm import tqdm

# ──── КОНФИГУРАЦИЯ ────────────────────────────────────────────────────────────
CONFIG = {
    "ffmpeg_path": r"C:\users\user\desktop\media_cleaner\ffmpeg\ffmpeg\bin\ffmpeg.exe",
    "epsilon_video": 0.120,  # Увеличено в 11 раз для более сильного шума (было 0.011)
    "epsilon_multiplier_strong": 1.8,  # Множитель для сильнейшей маскировки
    "num_eot_transforms": 4,  # Увеличено для лучшей robustness
    "default_every_n_frames": 10,
    "high_freq_base": 17000,
    "audio_levels": {
        "очень слабый": 0.0020,
        "слабый": 0.0035,
        "средний": 0.0050,
        "сильный": 0.0080
    },
    "supported_video": {'.mp4', '.mov', '.avi', '.mkv', '.webm'},
    "log_level": "INFO",
    "temp_folder_prefix": "_temp_adv_"
}

# ──── ЛОГИРОВАНИЕ ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('imperceptible_protected_video.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ──── ГЛОБАЛЬНАЯ КОНФИГУРАЦИЯ ────────────────────────────────────────────────
DEVICE = None  # Будет инициализировано в функции init_device()
_model = None  # Будет инициализировано в функции init_device()

def init_device(device_type: str = "auto"):
    """Инициализирует устройство (CPU/GPU) и модель."""
    global DEVICE, _model
    
    if device_type == "auto":
        DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    elif device_type == "gpu":
        if torch.cuda.is_available():
            DEVICE = torch.device("cuda")
        else:
            logger.warning("GPU недоступна, используем CPU")
            DEVICE = torch.device("cpu")
    else:
        DEVICE = torch.device("cpu")
    
    logger.info(f"Используется устройство: {DEVICE}")
    
    try:
        _model = models.resnet18(weights=ResNet18_Weights.IMAGENET1K_V1).to(DEVICE)
        _model.eval()
        _model.requires_grad_(False)
        logger.info("[OK] ResNet18 model loaded successfully")
    except Exception as e:
        logger.error(f"Ошибка загрузки модели ResNet18: {e}")
        _model = None

# Инициализируем по умолчанию при импорте
init_device("auto")

_preprocess = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


# ──── ФУНКЦИИ ПРОВЕРКИ ВИДЕО ─────────────────────────────────────────────────
def verify_video_changes(original_path: str, processed_path: str, frame_num: int = 0):
    """Проверяет изменения в видео путём сравнения кадров."""
    try:
        print(f"\n📊 Анализ изменений видео...")
        print(f"  Исходный файл: {original_path}")
        print(f"  Обработанный файл: {processed_path}")
        
        if not Path(original_path).exists() or not Path(processed_path).exists():
            print("❌ Один или оба файла не существуют")
            return False
        
        # Открыть видео
        original_cap = cv2.VideoCapture(original_path)
        processed_cap = cv2.VideoCapture(processed_path)
        
        if not original_cap.isOpened() or not processed_cap.isOpened():
            print("❌ Ошибка: не удаётся открыть видео файлы")
            return False
        
        # Получить информацию
        orig_fps = original_cap.get(cv2.CAP_PROP_FPS)
        orig_count = int(original_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_width = int(original_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_height = int(original_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        proc_fps = processed_cap.get(cv2.CAP_PROP_FPS)
        proc_count = int(processed_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        proc_width = int(processed_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        proc_height = int(processed_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"\n  📹 Параметры видео:")
        print(f"    Исходное:     {orig_width}x{orig_height} @ {orig_fps:.1f}fps, {orig_count} кадров")
        print(f"    Обработанное: {proc_width}x{proc_height} @ {proc_fps:.1f}fps, {proc_count} кадров")
        
        # Извлечь кадр
        original_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        processed_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        
        ret1, orig_frame = original_cap.read()
        ret2, proc_frame = processed_cap.read()
        
        if not ret1 or not ret2:
            print(f"❌ Не удаётся прочитать кадр #{frame_num}")
            return False
        
        # Приести к одному размеру для сравнения
        if orig_frame.shape != proc_frame.shape:
            proc_frame = cv2.resize(proc_frame, (orig_width, orig_height))
        
        # Конвертировать в float для точных вычислений
        orig_float = orig_frame.astype(np.float32)
        proc_float = proc_frame.astype(np.float32)
        
        # Вычислить различия
        diff = np.abs(orig_float - proc_float)
        mse = np.mean(diff ** 2)
        mae = np.mean(diff)
        max_diff = np.max(diff)
        
        # Процент изменённых пикселей
        changed_pixels = np.sum(diff > 5)
        total_pixels = diff.shape[0] * diff.shape[1] * diff.shape[2]
        percent_changed = (changed_pixels / total_pixels) * 100
        
        print(f"\n  🔍 Анализ кадра #{frame_num}:")
        print(f"    Mean Absolute Error (MAE): {mae:.2f}")
        print(f"    Mean Squared Error (MSE):  {mse:.2f}")
        print(f"    Max difference: {max_diff:.2f}")
        print(f"    Изменённых пикселей: {percent_changed:.2f}%")
        
        original_cap.release()
        processed_cap.release()
        
        if mse > 100:
            print("\n✅ Видео ИЗМЕНЕНО - обнаружены значительные различия")
            return True
        elif mse > 1:
            print("\n✅ Видео ИЗМЕНЕНО - обнаружены слабые различия")
            return True
        else:
            print("\n⚠️  Видео НЕ изменено - файлы практически идентичны")
            return False
    
    except Exception as e:
        logger.error(f"Ошибка при проверке видео: {e}")
        return False


def verify_metadata(video_path: str) -> bool:
    """Проверяет метаданные видео с помощью ffprobe."""
    try:
        ffprobe_path = CONFIG["ffmpeg_path"].replace("ffmpeg.exe", "ffprobe.exe")
        
        result = subprocess.run(
            [ffprobe_path, "-v", "quiet", "-print_format", "json", 
             "-show_format", video_path],
            capture_output=True, text=True, timeout=10
        )
        
        data = json.loads(result.stdout)
        tags = data.get("format", {}).get("tags", {})
        
        print(f"\n  📋 Метаданные файла:")
        if tags:
            print(f"    ⚠️  Найдены метаданные:")
            for key, value in list(tags.items())[:5]:  # Показываем первые 5
                print(f"      {key}: {value}")
            return False
        else:
            print(f"    ✅ Метаданные очищены (пусто)")
            return True
    
    except Exception as e:
        logger.debug(f"Ошибка при чтении метаданных: {e}")
        return False


# ──── ТРАНСФОРМАЦИИ ──────────────────────────────────────────────────────────
def choose_device() -> str:
    """Интерактивный выбор устройства обработки (CPU/GPU)."""
    print("\n" + "="*70)
    print("⚙️  ВЫБОР УСТРОЙСТВА ОБРАБОТКИ")
    print("="*70)
    
    has_gpu = torch.cuda.is_available()
    print(f"\nТекущее состояние:")
    print(f"  GPU доступна: {'✅ Да' if has_gpu else '❌ Нет'}")
    if has_gpu:
        print(f"  Модель GPU: {torch.cuda.get_device_name(0)}")
    
    print(f"\nОпции обработки:")
    print(f"  1️⃣  GPU (быстрее, требует NVIDIA с CUDA)")
    print(f"  2️⃣  CPU (медленнее, но стабильнее)")
    print(f"  3️⃣  Авто (выбрать автоматически)")
    
    choice = input(f"\nВыберите (1-3) [по умолчанию 3]: ").strip() or "3"
    
    device_map = {
        "1": "gpu",
        "2": "cpu",
        "3": "auto"
    }
    
    device_choice = device_map.get(choice, "auto")
    init_device(device_choice)
    
    print(f"\n✓ Используется: {DEVICE}\n")
    return str(DEVICE)


def random_distortion(tensor: torch.Tensor) -> torch.Tensor:
    """Применяет случайные трансформации к тензору для diversify атак."""
    t = tensor.clone()
    
    if np.random.rand() > 0.5:
        t = t + torch.randn_like(t) * 0.008
    
    if np.random.rand() > 0.6:
        brightness_factor = 1 + 0.08 * (torch.rand(1, device=DEVICE).item() - 0.5) * 2
        t = transforms.functional.adjust_brightness(t, brightness_factor)
        
        contrast_factor = 1 + 0.08 * (torch.rand(1, device=DEVICE).item() - 0.5) * 2
        t = transforms.functional.adjust_contrast(t, contrast_factor)
    
    return t


# ──── КЛАСС ДЛЯ ОБРАБОТКИ ВИДЕО ──────────────────────────────────────────────
class VideoProcessor:
    """Обработка видеофайлов с добавлением adversarial noise."""
    
    def __init__(self, epsilon: float = CONFIG["epsilon_video"], 
                 num_eot: int = CONFIG["num_eot_transforms"]):
        if _model is None:
            raise RuntimeError("Модель ResNet18 не загружена")
        
        self.model = _model
        self.preprocess = _preprocess
        self.epsilon = epsilon
        self.num_eot = num_eot
        self.device = DEVICE
    
    def add_imperceptible_video_noise(self, frame_bgr: np.ndarray, strength_mult: float = 1.0) -> np.ndarray:
        """Добавляет невидимый adversarial шум к кадру без потери качества."""
        try:
            original_h, original_w = frame_bgr.shape[:2]
            
            # Конвертируем в RGB float32 [0, 1]
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            
            # Убеждаемся что значения в диапазоне [0, 1]
            frame_rgb = np.clip(frame_rgb, 0.0, 1.0)
            
            # Создаём tensor оригинального размера (C, H, W) - СРАЗУ НА GPU
            frame_tensor_orig = torch.from_numpy(frame_rgb.copy()).permute(2, 0, 1).float().to(self.device)
            
            # Resize ДЛЯ МОДЕЛИ только (224x224)
            frame_224 = torch.nn.functional.interpolate(
                frame_tensor_orig.unsqueeze(0),
                size=(224, 224),
                mode='bicubic',
                align_corners=False
            ).squeeze(0)
            
            # Нормализуем для ResNet
            mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1).to(self.device)
            std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1).to(self.device)
            
            input_tensor = ((frame_224 - mean) / std).unsqueeze(0).to(self.device)
            
            total_grad = torch.zeros_like(input_tensor)
            
            # Ensemble of Transformations (EOT) для robustness
            for _ in range(self.num_eot):
                distorted = random_distortion(input_tensor.detach().clone())
                distorted.requires_grad_(True)
                
                with torch.enable_grad():
                    out = self.model(distorted)
                    label = out.argmax(dim=1)
                    # УСИЛЕННАЯ loss функция для более сильного шума
                    loss = F.cross_entropy(out, label) * 3.0
                    
                    self.model.zero_grad()
                    loss.backward()
                    
                    if distorted.grad is not None:
                        total_grad += distorted.grad.detach().clone()
            
            # Если градиент нулевой, возвращаем оригинальный кадр
            if total_grad.abs().sum() == 0:
                logger.debug("Нулевой градиент, кадр не изменён")
                return frame_bgr
            
            avg_grad = total_grad / self.num_eot
            
            # Интерполируем градиенты обратно на оригинальный размер
            grad_interp = torch.nn.functional.interpolate(
                avg_grad,
                size=(original_h, original_w),
                mode='bilinear',
                align_corners=False
            )
            
            # Подготавливаем оригинальный tensor для применения perturbation
            frame_tensor_orig_norm = ((frame_tensor_orig - mean) / std).unsqueeze(0).to(self.device)
            
            # FGSM атака с интерполированными градиентами и множителем силы
            epsilon_effective = self.epsilon * strength_mult
            perturbed = frame_tensor_orig_norm + epsilon_effective * grad_interp.sign()
            
            # Денормализуем
            perturbed_denorm = perturbed * std + mean
            perturbed_denorm = torch.clamp(perturbed_denorm, 0, 1)
            
            # Конвертируем в numpy (H, W, C) с аккуратным масштабированием
            perturbed_float = perturbed_denorm.squeeze(0).permute(1, 2, 0).cpu().numpy()
            # Убеждаемся что значения в корректном диапазоне перед преобразованием
            perturbed_float = np.clip(perturbed_float, 0.0, 1.0)
            perturbed_rgb = (perturbed_float * 255.0).astype(np.uint8)
            
            # Финальная проверка значений
            perturbed_rgb = np.clip(perturbed_rgb, 0, 255)
            
            # RGB -> BGR
            perturbed_bgr = cv2.cvtColor(perturbed_rgb, cv2.COLOR_RGB2BGR)
            
            # Очищаем GPU память
            del input_tensor, distorted, total_grad, avg_grad, grad_interp, frame_tensor_orig_norm, perturbed, perturbed_denorm
            torch.cuda.empty_cache()
            
            return perturbed_bgr
        
        except Exception as e:
            logger.error(f"Ошибка при добавлении видео-шума: {e}\n{traceback.format_exc()}")
            return frame_bgr
    
    def process_video(self, input_path: str, start_frame: int, end_frame: int, 
                     every_n_frames: int, video_strength_mult: float = 1.0,
                     should_cancel_fn=None) -> Tuple[str, int]:
        """
        Обрабатывает видео, добавляя шум к нужным кадрам.
        Возвращает (путь к временной папке, количество обработанных кадров)
        """
        base = Path(input_path).stem
        input_dir = Path(input_path).parent
        temp_folder = input_dir / f"{base}{CONFIG['temp_folder_prefix']}{every_n_frames}f"
        
        # Проверяем видеофайл
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise RuntimeError(f"Не удалось открыть видео: {input_path}")
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if total_frames == 0 or fps == 0:
                raise RuntimeError("Не удалось получить параметры видео")
            
            # Приводим размер к чётным числам (требование codec)
            w = w - (w % 2)
            h = h - (h % 2)
            
            logger.info(f"Параметры видео: {total_frames} кадров @ {fps}fps, {w}x{h}")
            
            # Создаём временную папку
            if temp_folder.exists():
                shutil.rmtree(temp_folder)
            temp_folder.mkdir(exist_ok=True)
            
            frame_idx = 0
            noisy_frames = 0
            
            # Обработка кадров с progress bar
            pbar = tqdm(total=total_frames, desc="Обработка видео", unit="кадр")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Проверка отмены задачи
                if should_cancel_fn and should_cancel_fn():
                    logger.info("Отмена обработки видео")
                    pbar.close()
                    return str(temp_folder), noisy_frames
                
                frame_idx += 1
                frame = cv2.resize(frame, (w, h))
                
                # Применяем шум только к нужным кадрам
                if start_frame <= frame_idx <= end_frame and frame_idx % every_n_frames == 0:
                    try:
                        perturbed = self.add_imperceptible_video_noise(frame, video_strength_mult)
                        cv2.imwrite(str(temp_folder / f"frame_{frame_idx:06d}.png"), perturbed)
                        noisy_frames += 1
                    except Exception as e:
                        logger.warning(f"Ошибка обработки кадра {frame_idx}, используется оригинал: {e}")
                        cv2.imwrite(str(temp_folder / f"frame_{frame_idx:06d}.png"), frame)
                else:
                    cv2.imwrite(str(temp_folder / f"frame_{frame_idx:06d}.png"), frame)
                
                pbar.update(1)
            
            pbar.close()
            
            logger.info(f"Обработано кадров: {frame_idx}, с шумом: {noisy_frames}")
            return str(temp_folder), noisy_frames
        
        finally:
            cap.release()


# ──── КЛАСС ДЛЯ ОБРАБОТКИ АУДИО ──────────────────────────────────────────────
class AudioProcessor:
    """Обработка звука с добавлением маскирования."""
    
    @staticmethod
    def add_imperceptible_audio_noise(audio_path_in: str, audio_path_out: str, 
                                      level: str = "слабый") -> None:
        """Добавляет невидимый шум к аудио."""
        try:
            if level not in CONFIG["audio_levels"]:
                logger.warning(f"Неизвестный уровень '{level}', используется 'слабый'")
                level = "слабый"
            
            std = CONFIG["audio_levels"][level]
            
            # Загружаем аудио
            y, sr = librosa.load(audio_path_in, sr=16000, mono=True)
            
            if len(y) == 0:
                raise ValueError("Аудио-трек пуст")
            
            # Вычисляем окружающий шум (psychoacoustic masking)
            rms = librosa.feature.rms(y=y)[0]
            envelope = np.interp(
                np.linspace(0, len(rms)-1, len(y)), 
                np.arange(len(rms)), 
                rms
            )
            envelope = np.clip(envelope / (np.max(envelope) + 1e-8), 0.04, 1.0) ** 1.5
            
            # Генерируем шум
            t = np.arange(len(y), dtype=np.float32) / sr
            
            # Высокочастотный синус (17 kHz) — неслышимая частота
            high_freq_mask = 0.0028 * np.sin(2 * np.pi * CONFIG["high_freq_base"] * t)
            
            # Белый гауссовский шум
            noise_base = np.random.normal(0, std, len(y))
            
            # Комбинируем с психоакустическим маскированием
            total_noise = (noise_base + high_freq_mask) * envelope
            
            # Применяем шум к аудио
            adv_audio = y + total_noise
            adv_audio = np.clip(adv_audio, -0.999, 0.999)
            
            # Сохраняем
            sf.write(audio_path_out, adv_audio, sr, subtype='PCM_16')
            logger.info(f"[AUDIO] Masking level '{level}' added -> {audio_path_out}")
        
        except Exception as e:
            logger.error(f"Ошибка при обработке аудио: {e}\n{traceback.format_exc()}")
            raise


# ──── ФУНКЦИИ ИНТЕРФЕЙСА ─────────────────────────────────────────────────────
def choose_epsilon() -> float:
    """Интерактивный выбор epsilon (силы шума) для видео."""
    print("\n" + "="*70)
    print("⚙️  ВЫБОР СИЛЫ ВИДЕО-ШУМА (epsilon)")
    print("="*70)
    
    recommendations = {
        "1": ("Очень слабый (практически не видно)", 0.040),
        "2": ("Слабый (рекомендуется для ярких видео)", 0.070),
        "3": ("Стандартный (рекомендуется по умолчанию)", 0.120),
        "4": ("Сильный (видно небольших артефактов)", 0.180),
        "5": ("Кастомное значение (ввести вручную)", None),
    }
    
    print("\nПредустановленные значения:")
    for key, (desc, value) in recommendations.items():
        if value is not None:
            print(f"  {key}️⃣  {desc} (epsilon={value})")
        else:
            print(f"  {key}️⃣  {desc}")
    
    print(f"\nТекущее значение по умолчанию: {CONFIG['epsilon_video']}")
    
    choice = input("\nВыберите (1-5) [по умолчанию 3]: ").strip() or "3"
    
    if choice == "5":
        while True:
            try:
                custom = float(input("Введите кастомное значение epsilon (0.01-0.5): "))
                if 0.01 <= custom <= 0.5:
                    print(f"✓ Выбрано: epsilon={custom}")
                    return custom
                else:
                    print("❌ Значение должно быть от 0.01 до 0.5")
            except ValueError:
                print("❌ Введите число!")
    elif choice in recommendations and recommendations[choice][1] is not None:
        desc, value = recommendations[choice]
        print(f"✓ Выбрано: {desc} (epsilon={value})")
        return value
    else:
        return CONFIG["epsilon_video"]


def choose_strength_multiplier() -> float:
    """Интерактивный выбор множителя силы шума в зависимости от обработки."""
    print("\n" + "="*70)
    print("⚙️  ВЫБОР МНОЖИТЕЛЯ СИЛЫ ШУМА (strength_mult)")
    print("="*70)
    
    presets = {
        "1": ("Минимальный (0.3x)", 0.3, "Для очень ярких видео, минимальные визуальные артефакты"),
        "2": ("Низкий (0.6x)", 0.6, "Для ярких видео, слабая защита"),
        "3": ("Средний (1.0x)", 1.0, "Сбалансированный вариант (рекомендуется)"),
        "4": ("Высокий (1.4x)", 1.4, "Для обычных видео, хорошая защита"),
        "5": ("Максимальный (1.8x)", 1.8, "Сильный шум, хорошо видно небольшие артефакты"),
        "6": ("Кастомное значение", None, "Ввести вручную"),
    }
    
    print("\nДоступные преsets:")
    for key, (name, value, desc) in presets.items():
        if value is not None:
            print(f"  {key}️⃣  {name}")
            print(f"       └─ {desc}")
        else:
            print(f"  {key}️⃣  {name}")
    
    choice = input("\nВыберите (1-6) [по умолчанию 3]: ").strip() or "3"
    
    if choice == "6":
        while True:
            try:
                custom = float(input("Введите кастомное значение (0.1-2.0): "))
                if 0.1 <= custom <= 2.0:
                    print(f"✓ Выбрано: strength_mult={custom}")
                    return custom
                else:
                    print("❌ Значение должно быть от 0.1 до 2.0")
            except ValueError:
                print("❌ Введите число!")
    elif choice in presets and presets[choice][1] is not None:
        name, value, desc = presets[choice]
        print(f"✓ Выбрано: {name}")
        return value
    else:
        return 1.0


def list_video_files() -> list:
    """Возвращает список видеофайлов в текущей папке с абсолютными путями."""
    current = Path('.').resolve()
    videos = [
        str(f.resolve()) for f in current.iterdir() 
        if f.is_file() and f.suffix.lower() in CONFIG["supported_video"]
        and not f.name.endswith('_protected.mp4')
        and not CONFIG['temp_folder_prefix'] in f.name
    ]
    return sorted(videos)


def choose_video() -> Optional[str]:
    """Интерактивный выбор видеофайла."""
    videos = list_video_files()
    if not videos:
        logger.error("В текущей папке НЕТ видео-файлов!")
        return None
    
    logger.info("\nДоступные видео в папке:")
    logger.info("-" * 70)
    for i, v in enumerate(videos, 1):
        logger.info(f"{i:2d} | {v}")
    logger.info("-" * 70)
    
    while True:
        try:
            num = input("Выберите номер видео (0 = выход): ").strip()
            if num == "0":
                return None
            idx = int(num) - 1
            if 0 <= idx < len(videos):
                return videos[idx]
            logger.warning(f"Введите число от 1 до {len(videos)}")
        except ValueError:
            logger.warning("Введите число!")
        except KeyboardInterrupt:
            return None


def choose_settings(total_frames: int) -> Tuple[int, int, Optional[str], int, float, float]:
    """Интерактивный выбор настроек обработки с подробными рекомендациями.
    Возвращает: (start_frame, end_frame, audio_level, every_n, video_strength_mult, epsilon)
    """
    print("\n" + "="*70)
    print("⚙️  НАСТРОЙКИ ОБРАБОТКИ ВИДЕО")
    print("="*70)
    print(f"\nОбщая информация:")
    print(f"  📹 Видео содержит {total_frames} кадров")
    print(f"  ⏱️  Примерная длительность: {total_frames / 30:.1f} сек (при 30fps)\n")
    
    # 1. Выбор диапазона кадров
    print("[1/4] ДИАПАЗОН ОБРАБОТКИ")
    print("-" * 70)
    print("1️⃣  Применить шум ко ВСЕМУ видео")
    print("2️⃣  Выбрать диапазон (от кадра X до кадра Y)")
    
    choice = input("\nВыберите (1 или 2) [по умолчанию 1]: ").strip() or "1"
    
    start_frame = 1
    end_frame = total_frames
    
    if choice == "2":
        while True:
            try:
                start = int(input(f"  Начало (от 1 до {total_frames}): "))
                end = int(input(f"  Конец (от {start} до {total_frames}): "))
                if 1 <= start <= end <= total_frames:
                    start_frame = start
                    end_frame = end
                    print(f"  ✓ Выбрано: кадры {start_frame}–{end_frame}")
                    break
                else:
                    print(f"  ❌ Ошибка: введите числа в диапазоне 1–{total_frames}")
            except ValueError:
                print("  ❌ Введите числа!")
    else:
        print(f"  ✓ Выбрано: кадры 1–{total_frames} (все видео)")
    
    # 2. Выбор силы видео-шума (epsilon)
    print("\n[2/4] СИЛА ВИДЕО-ШУМА")
    print("-" * 70)
    epsilon = choose_epsilon()
    
    # 3. Выбор множителя силы (strength_mult)
    print("\n[3/4] МНОЖИТЕЛЬ ДОПОЛНИТЕЛЬНОЙ СИЛЫ")
    print("-" * 70)
    video_strength_mult = choose_strength_multiplier()
    
    # 4. Частота применения шума
    print("\n[4/4] ЧАСТОТА ПРИМЕНЕНИЯ ШУМА")
    print("-" * 70)
    print("1️⃣  Каждый кадр (лучше всего, без мерцания)")
    print("2️⃣  Каждый 5-й кадр (быстрее, может быть мерцание)")
    print("3️⃣  Каждый 10-й кадр (самый быстрый вариант)")
    
    freq_choice = input("\nВыберите (1-3) [по умолчанию 1]: ").strip() or "1"
    every_n = 1 if freq_choice == "1" else 5 if freq_choice == "2" else 10
    print(f"  ✓ Выбрано: шум каждые {every_n} кадров")
    
    # Аудио-маскировка (опциональна)
    print("\n" + "="*70)
    print("🔊 АУДИО-МАСКИРОВКА (опциональна)")
    print("="*70)
    print("\nЗамечание: рекомендуется оставить БЕЗ маскировки (пропусти эту часть)")
    print("\n1️⃣  БЕЗ маскировки аудио (рекомендуется)")
    print("2️⃣  Применить маскировку (слабую)")
    print("3️⃣  Применить маскировку (среднюю)")
    print("4️⃣  Применить маскировку (сильную)")
    
    audio_choice = input("\nВыберите (1-4) [по умолчанию 1]: ").strip() or "1"
    
    audio_level = None
    if audio_choice == "2":
        audio_level = "слабый"
        print(f"  ✓ Выбрано: слабое маскирование аудио")
    elif audio_choice == "3":
        audio_level = "средний"
        print(f"  ✓ Выбрано: среднее маскирование аудио")
    elif audio_choice == "4":
        audio_level = "сильный"
        print(f"  ✓ Выбрано: сильное маскирование аудио")
    else:
        print(f"  ✓ Выбрано: без маскировки (аудио не изменяется)")
    
    # Итоговое резюме
    print("\n" + "="*70)
    print("📋 ИТОГОВЫЕ НАСТРОЙКИ")
    print("="*70)
    print(f"  Диапазон: кадры {start_frame}–{end_frame}")
    print(f"  Epsilon (сила шума): {epsilon}")
    print(f"  Множитель: {video_strength_mult}x")
    print(f"  Частота: каждые {every_n} кадров")
    print(f"  Аудио: {'без маскировки' if audio_level is None else f'маскировка ({audio_level})'}")
    print("="*70 + "\n")
    
    return start_frame, end_frame, audio_level, every_n, video_strength_mult, epsilon


def extract_audio(input_path: str, output_path: str) -> None:
    """Извлекает аудио из видео с помощью ffmpeg (без метаданных)."""
    try:
        result = subprocess.run([
            CONFIG["ffmpeg_path"], "-y", "-i", input_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000",
            "-map_metadata", "-1",  # Удаление метаданных аудио
            output_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg ошибка: {result.stderr}")
        
        logger.info(f"[AUDIO] Extracted -> {output_path}")
    
    except Exception as e:
        logger.error(f"Ошибка извextraction аудио: {e}")
        raise


def check_gpu_encoder() -> str:
    """Проверяет доступность GPU кодеков NVIDIA и возвращает лучший доступный."""
    try:
        # Проверяем доступные GPU кодеки
        encoders_check = subprocess.run(
            [CONFIG["ffmpeg_path"], "-codecs"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        
        output = encoders_check.stdout
        
        # Проверяем HEVC GPU кодек (лучше всего)
        if "hevc_nvenc" in output:
            logger.info("[GPU] Using encoder: HEVC NVENC (fastest)")
            return "hevc_nvenc"
        
        # Проверяем H.264 GPU кодек
        if "h264_nvenc" in output:
            logger.info("[GPU] Using encoder: H.264 NVENC")
            return "h264_nvenc"
        
        # Fallback на CPU кодек
        logger.warning("[WARN] GPU codecs unavailable, using CPU codec (slower)")
        return "libx264"
    
    except Exception as e:
        logger.warning(f"Ошибка проверки GPU кодеков: {e}, используется CPU")
        return "libx264"


def assemble_video(temp_folder: str, audio_path: str, fps: float, output_path: str, use_gpu: bool = True) -> None:
    """Собирает видео из кадров с добавлением аудио и удалением метаданных."""
    try:
        # Выбираем кодек в зависимости от наличия GPU
        if use_gpu:
            encoder = check_gpu_encoder()
        else:
            encoder = "libx264"
            logger.info("📺 Используется CPU кодек: libx264")
        
        # Параметры кодирования в зависимости от типа кодека
        if encoder in ["hevc_nvenc", "h264_nvenc"]:
            # GPU кодирование (NVIDIA NVENC)
            video_codec_params = [
                "-c:v", encoder,
                "-pix_fmt", "yuv420p",  # ВАЖНО: явно указываем формат пиксела для совместимости
                "-rc", "vbr",  # Variable bitrate для лучшего качества
                "-cq", "23",   # Quality level (0-51, ниже = лучше)
                "-preset", "fast"  # fast/medium/slow
            ]
        else:
            # CPU кодирование
            video_codec_params = [
                "-c:v", encoder,
                "-pix_fmt", "yuv420p",
                "-preset", "fast"  # Быстрая кодирование на CPU
            ]
        
        ffmpeg_cmd = [
            CONFIG["ffmpeg_path"], "-y",
            "-framerate", str(fps),
            "-i", str(Path(temp_folder) / "frame_%06d.png"),
            "-i", audio_path
        ] + video_codec_params + [
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-map_metadata", "-1",  # Удаление метаданных
            output_path
        ]
        
        result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg ошибка: {result.stderr}")
        
        logger.info(f"[OK] Video assembled via {encoder} -> {output_path}")
    
    except Exception as e:
        logger.error(f"Ошибка сборки видео: {e}")
        raise


def cleanup_temps(temp_folder: str, *temp_files: str) -> None:
    """Очищает временные файлы."""
    try:
        if Path(temp_folder).exists():
            shutil.rmtree(temp_folder)
            logger.info(f"Удалена временная папка: {temp_folder}")
        
        for tmp_file in temp_files:
            if Path(tmp_file).exists():
                Path(tmp_file).unlink()
        
        logger.info("Временные файлы очищены")
    
    except Exception as e:
        logger.warning(f"Не удалось полностью очистить временные файлы: {e}")


def strip_metadata(file_path: str) -> None:
    """Удаляет все метаданные из видеофайла."""
    try:
        temp_path = f"{file_path}.tmp.mp4"
        
        result = subprocess.run([
            CONFIG["ffmpeg_path"], "-y", "-i", file_path,
            "-c:v", "copy",
            "-c:a", "copy",
            "-map_metadata", "-1",
            temp_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            logger.warning(f"Не удалось удалить метаданные: {result.stderr}")
            if Path(temp_path).exists():
                Path(temp_path).unlink()
            return
        
        # Заменяем оригинальный файл на очищенный
        Path(temp_path).replace(file_path)
        logger.info(f"[OK] Metadata removed from {file_path}")
    
    except Exception as e:
        logger.warning(f"Ошибка при удалении метаданных: {e}")


# ──── ГЛАВНАЯ ФУНКЦИЯ ────────────────────────────────────────────────────────
def process_imperceptible_protected_video(input_path: str) -> bool:
    """
    Главная функция обработки видео.
    Возвращает True если успешно, False иначе.
    """
    try:
        base = Path(input_path).stem
        input_dir = Path(input_path).parent
        temp_folder = str(input_dir / f"{base}{CONFIG['temp_folder_prefix']}_frames")
        temp_audio_orig = str(input_dir / f"{base}_audio_orig.wav")
        temp_audio_adv = str(input_dir / f"{base}_audio_adv.wav")
        output_final = str(input_dir / f"{base}_protected.mp4")
        
        logger.info(f"\n{'='*70}")
        logger.info(f"Запуск защиты видео")
        logger.info(f"Файл: {input_path}")
        logger.info(f"{'='*70}\n")
        
        # Проверяем входной файл
        if not Path(input_path).exists():
            raise FileNotFoundError(f"Файл не найден: {input_path}")
        
        # Получаем параметры видео
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise RuntimeError(f"Не удалось открыть видео: {input_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        # Получаем настройки от пользователя
        start_frame, end_frame, audio_level, every_n, video_strength_mult, epsilon = choose_settings(total_frames)
        
        # Обработка видео с кастомным epsilon
        logger.info("\n[1/3] Обработка видео (кодирование на GPU)...")
        video_processor = VideoProcessor(epsilon=epsilon)
        temp_folder, noisy_frames = video_processor.process_video(
            input_path, start_frame, end_frame, every_n, video_strength_mult
        )
        
        # Извлечение аудио
        logger.info("\n[2/3] Обработка аудио...")
        extract_audio(input_path, temp_audio_orig)
        
        # Обработка аудио (если нужна маскировка)
        audio_processor = AudioProcessor()
        if audio_level is not None:
            logger.info(f"     Применяю маскировку аудио уровня '{audio_level}'...")
            audio_processor.add_imperceptible_audio_noise(temp_audio_orig, temp_audio_adv, audio_level)
            final_audio = temp_audio_adv
        else:
            logger.info("     Маскировка аудио отключена (используется оригинальное)")
            final_audio = temp_audio_orig
        
        # Сборка финального видео через GPU
        logger.info("\n[3/3] Сборка видео через видеокарту...")
        assemble_video(temp_folder, final_audio, fps, output_final, use_gpu=True)
        
        # Очистка
        logger.info("\nОчистка временных файлов...")
        cleanup_temps(temp_folder, temp_audio_orig, temp_audio_adv)
        
        # Удаление метаданных из финального файла
        logger.info("Удаление метаданных из видео...")
        strip_metadata(output_final)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"[DONE] Complete! Processed {total_frames} frames, {noisy_frames} with noise")
        logger.info(f"[OK] Final file: {output_final}")
        logger.info(f"[OK] Parameters: epsilon={epsilon}, strength_mult={video_strength_mult}x")
        logger.info(f"{'='*70}\n")
        
        return True
    
    except Exception as e:
        logger.error(f"\n[CRITICAL] Error: {e}\n{traceback.format_exc()}")
        return False


# ──── ГЛАВНЫЙ ЦИКЛ ──────────────────────────────────────────────────────────
def main():
    """Главный цикл программы."""
    logger.info("╔" + "="*68 + "╗")
    logger.info("║ Imperceptible Protected Video Generator v2.0                         ║")
    logger.info("║ Максимально незаметная защита от CV и ASR                            ║")
    logger.info("╚" + "="*68 + "╝\n")
    
    # Выбор устройства обработки при старте
    choose_device()
    
    while True:
        try:
            selected = choose_video()
            if selected is None:
                logger.info("\nВыход...")
                break
            
            success = process_imperceptible_protected_video(selected)
            
            if success:
                # Предложить проверку видео
                check = input("\n🔍 Проверить изменения в видео? (y/n): ").lower().strip()
                if check == 'y':
                    # Найти исходный файл для сравнения
                    original_dir = Path(selected).parent
                    output_file = original_dir / f"{Path(selected).stem}_protected{Path(selected).suffix}"
                    
                    if output_file.exists():
                        print()
                        verify_metadata(str(output_file))
                        verify_video_changes(selected, str(output_file), frame_num=0)
                    else:
                        print(f"❌ Обработанный файл не найден: {output_file}")
                
                again = input("\nОбработать ещё одно видео? (y/n): ").lower().strip()
                if again != 'y':
                    logger.info("Спасибо за использование!")
                    break
            else:
                retry = input("Повторить? (y/n): ").lower().strip()
                if retry != 'y':
                    break
        
        except KeyboardInterrupt:
            logger.info("\n\nПрограмма прервана пользователем.")
            break
        except Exception as e:
            logger.error(f"Неожиданная ошибка в главном цикле: {e}\n{traceback.format_exc()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Критическая ошибка при старте: {e}\n{traceback.format_exc()}")
        sys.exit(1)
