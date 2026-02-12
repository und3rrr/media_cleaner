# Архитектура Imperceptible Protected Video Generator v2.0

## Обзор системы

```
┌─────────────────────────────────────────────────────────┐
│  Пользователь запускает программу                       │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│ choose_video()   │  │ choose_settings()│
│ + Список видео   │  │ + Диапазон       │
│ + Интерфейс      │  │ + Уровень звука  │
└────────┬─────────┘  │ + Частота        │
         │            └──────────┬───────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ VideoProcessor             │
        │ + process_video()          │
        │   ├─ Читает кадры          │
        │   ├─ Добавляет шум (FGSM)  │
        │   └─ Сохраняет PNG         │
        └────────────┬───────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    ┌────────┐ ┌─────────┐ ┌──────────┐
    │ extract│ │AudioProc│ │assemble_ │
    │ _audio │ │essor    │ │video()   │
    │   ()   │ │  + Шум  │ │ + ffmpeg │
    │        │ │ + Маски │ │          │
    └────────┘ └─────────┘ └──────────┘
         │           │           │
         └───────────┼───────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ cleanup_temps()        │
        │ + Удаляет PNG          │
        │ + Удаляет WAV          │
        │ + Логирует             │
        └────────────┬───────────┘
                     │
                     ▼
         ┌──────────────────────┐
         │ Output: _protected.mp4
         └──────────────────────┘
```

---

## Компоненты

### 1. **CONFIG** (Глобальная конфигурация)
```python
CONFIG = {
    "ffmpeg_path": str,              # Путь к ffmpeg.exe
    "epsilon_video": float,           # Сила adversarial возмущения
    "num_eot_transforms": int,        # Кол-во трансформаций для EOT
    "high_freq_base": int,            # Частота неслышимого тона
    "audio_levels": dict,             # Уровни маскировки звука
    "supported_video": set,           # Поддерживаемые расширения
}
```

### 2. **random_distortion(tensor)** → torch.Tensor
Применяет случайные трансформации к кадру для robustness:
- Добавляет гауссовский шум (50% вероятность)
- Изменяет brightness (60% вероятность)
- Изменяет contrast (60% вероятность)

**Зачем?** Чтобы adversarial noise работал даже при небольших изменениях изображения (compression, rotation, и т.д.).

### 3. **VideoProcessor** (Класс для работы с видео)

#### Метод: `__init__(epsilon, num_eot)`
Инициализирует процессор с параметрами:
- Загружает ResNet18 модель
- Сохраняет параметры атаки
- Выбирает устройство (GPU или CPU)

#### Метод: `add_imperceptible_video_noise(frame_bgr: np.ndarray) → np.ndarray`

**Алгоритм FGSM (Fast Gradient Sign Method)**:

```
1. frame → ResNet18 → вывод softmax → label (самый вероятный класс)

2. Повторяем `num_eot` раз:
   - Применяем случайную трансформацию
   - Вычисляем loss = cross_entropy(output, label)
   - Берём gradients относительно пикселей
   - Аккумулируем gradients

3. Усредняем gradients по трансформациям

4. perturbation = epsilon * sign(average_gradient)

5. perturbed_frame = clamp(frame + perturbation, 0, 1)

6. Возвращаем perturbed_frame
```

**Почему это работает?**
- Нейросеть обучена на "естественных" картинках
- Мы двигаем пиксели в направлении максимально неправильного ответа
- Шум очень маленький, но направленный
- Человеческий глаз не видит такие мелкие изменения

#### Метод: `process_video(input_path, start_frame, end_frame, every_n_frames)`

```
for каждого кадра:
    если кадр в диапазоне и номер % every_n == 0:
        вызовем add_imperceptible_video_noise()
        сохраняем как PNG
    иначе:
        сохраняем оригинальный кадр как PNG
```

**Почему PNG?**
- Без потерь (lossless compression)
- Гарантирует, что каждый пиксель сохранён точно
- JPEG бы развалил наш аккуратный adversarial шум

**Progress bar (tqdm)**:
```
Обработка видео |████████░░| 45% [450/1000, 00:30<00:40, 15 fps]
```

---

### 4. **AudioProcessor** (Статический класс для работы со звуком)

#### Метод: `add_imperceptible_audio_noise(audio_in, audio_out, level)`

**Алгоритм маскировки**:

```
1. Загружаем WAV → преобразуем в 16 kHz mono

2. Вычисляем психоакустическую огибающую:
   - RMS (root mean square) каждого блока
   - Интерполируем для каждого сэмпла
   - Нормализуем и усиливаем (power=1.5)

3. Генерируем шум:
   a) Высокочастотный синус (17 kHz):
      sound_17k = 0.0028 * sin(2π * 17000 * t)
      
   b) Белый гауссовский шум:
      noise = normal(0, std_level)
   
   c) Комбинируем:
      total_noise = (noise + sound_17k) * envelope

4. Применяем к оригиналу:
   audio_protected = clamp(audio_original + total_noise, -0.999, 0.999)

5. Сохраняем как WAV 16-bit
```

**Почему это работает?**

1. **Высокочастотный синус (17 kHz)**:
   - Большинство взрослых (>25 лет) не слышат выше 15 kHz
   - Молодые люди могут услышать, но очень тихо
   - Для нейросетей это просто входной сигнал

2. **Белый шум + psychoacoustic masking**:
   - Маскируется исходным звуком (психоакустический эффект)
   - Усиливается только в громких местах
   - В тихих местах почти не слышно
   - Для Whisper это критическая помеха

3. **Психоакустическое маскирование**:
   ```
   envelope = RMS^1.5
   
   Громкий звук → envelope близка к 1.0 → шум усилен
   Тихий звук  → envelope близка к 0.0 → шум подавлен
   ```

---

### 5. **Вспомогательные функции**

#### `extract_audio(input_path, output_path)`
```bash
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 audio.wav
```
- `-vn` = no video
- `-acodec pcm_s16le` = 16-bit PCM
- `-ar 16000` = 16 kHz sample rate

#### `assemble_video(temp_folder, audio_path, fps, output_path)`
```bash
ffmpeg -framerate 30 -i frame_%06d.png -i audio.wav \
  -c:v libx264 -pix_fmt yuv420p \
  -c:a aac -b:a 128k \
  -shortest output.mp4
```
- `-c:v libx264` = H.264 кодек
- `-pix_fmt yuv420p` = совместимость с плеерами
- `-shortest` = синхронизация видео и аудио

#### `cleanup_temps(temp_folder, *temp_files)`
Удаляет временные файлы с обработкой ошибок.

#### `list_video_files()`
Сканирует папку и возвращает список видеофайлов.

#### `choose_video() → Optional[str]`
Интерактивный выбор видео с валидацией.

#### `choose_settings(total_frames) → Tuple[int, int, str, int]`
Возвращает: (start_frame, end_frame, audio_level, every_n_frames)

---

## Поток обработки

### Фаза 1: Инициализация
```python
video_processor = VideoProcessor()  # Загружает ResNet18
audio_processor = AudioProcessor()  # Готов к использованию
```

### Фаза 2: Обработка видео
```
cap = cv2.VideoCapture(input_path)
fps = cap.get(FPS)
total_frames = cap.get(FRAME_COUNT)

for frame in cap:
    if frame_number in range(start, end) and frame_number % every_n == 0:
        perturbed = video_processor.add_imperceptible_video_noise(frame)
        cv2.imwrite(f"frame_{frame_number:06d}.png", perturbed)
    else:
        cv2.imwrite(f"frame_{frame_number:06d}.png", frame)
```

### Фаза 3: Обработка аудио
```
y, sr = librosa.load(audio_path, sr=16000)
envelope = compute_psychoacoustic_envelope(y)
noise = generate_noise(len(y), envelope)
y_protected = y + noise
soundfile.write(output_audio, y_protected, sr)
```

### Фаза 4: Сборка видео
```bash
ffmpeg -framerate {fps} -i "frame_%06d.png" \
       -i "audio_protected.wav" \
       ... -shortest output.mp4
```

### Фаза 5: Очистка
```
shutil.rmtree(temp_folder)  # Удаляем PNG
os.remove(temp_audio_orig)  # Удаляем WAV
os.remove(temp_audio_adv)   # Удаляем защищённый WAV
```

---

## Обработка ошибок

### Стратегия

```
try:
    # Критичный код
except SpecificException as e:
    logger.error(f"Детальная ошибка: {e}\n{traceback.format_exc()}")
    # Fallback (если возможен)
    return fallback_value
finally:
    # Очистка (всегда выполняется)
    cleanup_resources()
```

### Примеры обработки

1. **Ошибка открытия видео**
   ```python
   cap = cv2.VideoCapture(input_path)
   if not cap.isOpened():
       raise RuntimeError(f"Не удалось открыть: {input_path}")
   ```

2. **Ошибка процесса пикселя**
   ```python
   try:
       perturbed = self.add_imperceptible_video_noise(frame)
   except Exception as e:
       logger.warning(f"Ошибка кадра {idx}, используем оригинал")
       cv2.imwrite(path, frame)  # Fallback
   ```

3. **Ошибка FFmpeg**
   ```python
   result = subprocess.run(ffmpeg_cmd, ...)
   if result.returncode != 0:
       raise RuntimeError(f"FFmpeg: {result.stderr}")
   ```

---

## Оптимизация производительности

### 1. **GPU vs CPU**
```python
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# GPU: ~100 фр/сек
# CPU: ~10 фр/сек
```

### 2. **Memory Management**
```python
# Удаляем использованные тензоры
del input_tensor, perturbed, total_grad
torch.cuda.empty_cache()
```

### 3. **Batch Processing**
Текущий код обрабатывает кадры по одному. Возможно улучшение:
```python
# Потенциальное улучшение:
batch_size = 4
for i in range(0, total_frames, batch_size):
    batch = frames[i:i+batch_size]
    perturbed_batch = model(batch)
    # ...
```

### 4. **PNG vs JPEG**
- PNG: без потерь, но медленнее записывать
- JPEG: быстрее, но потеряет adversarial информацию
- **Выбор**: PNG правильный

---

## Тестирование эффективности

### Как проверить, работает ли защита?

1. **OpenAI Whisper** (ASR):
   ```python
   import whisper
   model = whisper.load_model("base")
   
   # Оригинальное видео
   result_orig = model.transcribe("video.mp4")
   
   # Защищённое видео
   result_prot = model.transcribe("video_protected.mp4")
   
   # Сравнить WER (Word Error Rate)
   ```

2. **Google Cloud Vision** (CV):
   ```
   Загрузить оригинальное видео
   Загрузить защищённое видео
   Сравнить результаты распознавания объектов
   ```

3. **Визуальная проверка**:
   ```
   Открыть оба видео в плеере
   Они должны выглядеть одинаково для человека
   ```

---

## Возможные улучшения (TODO)

1. **Поддержка других моделей**
   - VGG16, ResNet50 (более точные)
   - ViT (Vision Transformer)

2. **Улучшение аудио маскирования**
   - Использовать MFCC вместо RMS
   - Добавить гармонический шум
   - Временная фильтрация

3. **Batch processing для видео**
   - Обрабатывать несколько кадров одновременно
   - Значительное ускорение

4. **Поддержка потокового видео**
   - Real-time обработка
   - Прямая трансляция с защитой

5. **WebUI**
   - Веб-интерфейс вместо CLI
   - Мониторинг прогресса в браузере

6. **CLI аргументы**
   ```bash
   python media_cleaner.py -i video.mp4 -o output.mp4 \
     --epsilon 0.015 --audio-level strong
   ```

---

## Структура логирования

```
imperceptible_protected_video.log
├── [INFO] Используется устройство: cuda
├── [INFO] Параметры видео: 1800 кадров @ 30.0fps, 1920x1080
├── [INFO] Обработано кадров: 1800, с шумом: 180
├── [INFO] Аудио извлечено → video_audio_orig.wav
├── [INFO] Аудио-маскировка уровня 'слабый' добавлена
├── [INFO] ✓ Видео собрано → video_protected.mp4
├── [INFO] Удалена временная папка: video_temp
├── [INFO] Временные файлы очищены
└── [ERROR] Критическая ошибка: [error message] (если есть)
```

---

## Выводы

Архитектура программы:
- ✅ **Модульная**: Классы VideoProcessor и AudioProcessor
- ✅ **Надёжная**: Полная обработка ошибок
- ✅ **Быстрая**: GPU поддержка, оптимизированный код
- ✅ **Логируемая**: Детальные логи для отладки
- ✅ **Масштабируемая**: Легко добавить новые модели и параметры
