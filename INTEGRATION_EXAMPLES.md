# Примеры интеграции Media Cleaner Server

## Пример 1: Базовое использование через Python

```python
from client import MediaCleanerClient
from pathlib import Path

# Инициализация клиента
client = MediaCleanerClient("http://your-server:8000")

# Загрузить видео
video_path = "videos/presentation.mp4"
result = client.upload_video(
    video_path,
    epsilon=0.12,
    audio_level="средний",
    user_id="user_123"
)

task_id = result['task_id']
print(f"Задача создана: {task_id}")

# Ждём завершения (с периодической проверкой)
task = client.wait_for_completion(task_id, check_interval=10)

if task['status'] == 'completed':
    # Скачиваем результат
    output = client.download_result(task_id, output_path="./results")
    print(f"✅ Файл сохранён: {output}")
else:
    print(f"❌ Ошибка: {task['error_message']}")
```

## Пример 2: Batch обработка (обработка много видео)

```python
from client import MediaCleanerClient
from pathlib import Path
import time

client = MediaCleanerClient("http://your-server:8000")

# Список видео для обработки
videos = Path("./videos").glob("*.mp4")

tasks = {}

# Загрузить все видео
print("📤 Загрузка видео...")
for video_path in videos:
    result = client.upload_video(
        str(video_path),
        epsilon=0.15,
        user_id="batch_user"
    )
    tasks[result['task_id']] = video_path.name
    print(f"  ✓ {video_path.name} → {result['task_id']}")

print(f"\n⏳ Ожидание обработки {len(tasks)} видео...")

# Ждём все задачи
completed = 0
failed = 0

for task_id, filename in tasks.items():
    task = client.wait_for_completion(task_id, timeout=3600)
    
    if task['status'] == 'completed':
        client.download_result(task_id, output_path="./results")
        print(f"✅ {filename}")
        completed += 1
    else:
        print(f"❌ {filename}: {task['error_message']}")
        failed += 1

print(f"\n📊 Итого: {completed} успешно, {failed} ошибок")
```

## Пример 3: Веб приложение (Flask)

```python
from flask import Flask, request, jsonify, send_file
from client import MediaCleanerClient
import os
from pathlib import Path

app = Flask(__name__)
client = MediaCleanerClient("http://localhost:8000")

UPLOAD_FOLDER = "./uploads"
RESULTS_FOLDER = "./results"

@app.route('/api/upload', methods=['POST'])
def upload_video():
    """API для загрузки видео"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    user_id = request.form.get('user_id', 'anonymous')
    
    # Сохранить временно
    temp_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(temp_path)
    
    try:
        # Загрузить на сервер обработки
        result = client.upload_video(
            temp_path,
            epsilon=float(request.form.get('epsilon', 0.12)),
            audio_level=request.form.get('audio_level', 'слабый'),
            user_id=user_id
        )
        
        # Удалить временный файл
        os.remove(temp_path)
        
        return jsonify({
            'status': 'success',
            'task_id': result['task_id'],
            'message': 'Video uploaded successfully'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """Получить статус задачи"""
    try:
        task = client.get_task_status(task_id)
        return jsonify({
            'status': task['status'],
            'progress': task['progress'],
            'error': task.get('error_message')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/api/download/<task_id>', methods=['GET'])
def download(task_id):
    """Скачать обработанное видео"""
    try:
        # Скачать с сервера обработки
        output_file = client.download_result(task_id, output_path=RESULTS_FOLDER)
        return send_file(output_file, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404


if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    app.run(debug=True, port=5000)
```

## Пример 4: Веб интерфейс (HTML + JavaScript)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Media Cleaner - Защита видео</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; }
        .container { border: 1px solid #ddd; padding: 20px; border-radius: 5px; }
        input, button { padding: 10px; margin: 5px; }
        .progress { margin: 20px 0; }
        .status { padding: 10px; background: #f0f0f0; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Media Cleaner Server</h1>
        
        <h3>Загрузить видео</h3>
        <input type="file" id="videoFile" accept="video/*">
        
        <label>
            Сила шума (epsilon):
            <input type="number" id="epsilon" value="0.12" min="0.04" max="0.20" step="0.01">
        </label>
        
        <label>
            Маскировка аудио:
            <select id="audioLevel">
                <option value="None">Отключить</option>
                <option value="слабый" selected>Слабый</option>
                <option value="средний">Средний</option>
                <option value="сильный">Сильный</option>
            </select>
        </label>
        
        <button onclick="uploadVideo()">📤 Загрузить</button>
        
        <div id="uploadStatus"></div>
        
        <hr>
        
        <h3>Проверить статус</h3>
        <input type="text" id="taskId" placeholder="Введите task_id">
        <button onclick="checkStatus()">🔍 Проверить</button>
        
        <div class="status" id="taskStatus" style="display:none;"></div>
        <div class="progress" id="progressBar" style="display:none;">
            <div style="width: 0%; height: 20px; background: #4CAF50;"></div>
        </div>
        
        <button id="downloadBtn" onclick="downloadVideo()" style="display:none;">
            📥 Скачать результат
        </button>
    </div>

    <script>
        let currentTaskId = null;

        async function uploadVideo() {
            const file = document.getElementById('videoFile').files[0];
            if (!file) {
                alert('Выберите видео');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);
            formData.append('epsilon', document.getElementById('epsilon').value);
            formData.append('audio_level', document.getElementById('audioLevel').value);

            document.getElementById('uploadStatus').innerHTML = '⏳ Загрузка...';

            try {
                const response = await fetch('http://your-server:8000/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.status === 'success') {
                    currentTaskId = data.task_id;
                    document.getElementById('uploadStatus').innerHTML = 
                        `✅ Видео загружено!<br>Task ID: <strong>${currentTaskId}</strong><br>` +
                        `Статус: ${data.task.status_text}`;
                    
                    // Автоматически проверяем статус
                    checkStatusPeriodically(currentTaskId);
                } else {
                    document.getElementById('uploadStatus').innerHTML = 
                        `❌ Ошибка: ${data.detail}`;
                }
            } catch (error) {
                document.getElementById('uploadStatus').innerHTML = 
                    `❌ Ошибка при загрузке: ${error}`;
            }
        }

        async function checkStatus() {
            const taskId = document.getElementById('taskId').value || currentTaskId;
            if (!taskId) {
                alert('Введите task_id');
                return;
            }

            try {
                const response = await fetch(`http://your-server:8000/task/${taskId}`);
                const data = await response.json();
                const task = data.task;

                const statusDiv = document.getElementById('taskStatus');
                statusDiv.style.display = 'block';
                statusDiv.innerHTML = `
                    <strong>Status:</strong> ${task.status_text}<br>
                    <strong>Progress:</strong> ${task.progress.toFixed(0)}%<br>
                    <strong>Input:</strong> ${task.input_video}<br>
                    ${task.output_video ? `<strong>Output:</strong> ${task.output_video}` : ''}<br>
                    ${task.error_message ? `<strong>Error:</strong> ${task.error_message}` : ''}
                `;

                // Обновить прогресс бар
                const progressBar = document.getElementById('progressBar');
                progressBar.style.display = 'block';
                progressBar.querySelector('div').style.width = task.progress + '%';

                // Показать кнопку скачивания если завершено
                const downloadBtn = document.getElementById('downloadBtn');
                if (task.status === 'completed') {
                    downloadBtn.style.display = 'block';
                    downloadBtn.onclick = () => downloadVideo(taskId);
                } else {
                    downloadBtn.style.display = 'none';
                }

                // Продолжить проверку если обрабатывается
                if (task.status === 'processing') {
                    setTimeout(() => checkStatus(), 5000);
                }

            } catch (error) {
                document.getElementById('taskStatus').innerHTML = 
                    `❌ Ошибка: ${error}`;
            }
        }

        async function checkStatusPeriodically(taskId) {
            setInterval(() => {
                document.getElementById('taskId').value = taskId;
                checkStatus();
            }, 5000);
        }

        async function downloadVideo(taskId) {
            taskId = taskId || currentTaskId;
            if (!taskId) {
                alert('Task ID не найден');
                return;
            }

            window.location.href = `http://your-server:8000/download/${taskId}`;
        }
    </script>
</body>
</html>
```

## Пример 5: Integrация с webhook (отправка результатов на URL)

```python
import httpx
from queue_processor import processing_queue, TaskStatus
import json

async def notify_webhook(task_id: str, webhook_url: str):
    """Отправить результаты на webhook"""
    task = processing_queue.get_task(task_id)
    
    payload = {
        "task_id": task_id,
        "status": task.status,
        "input_video": task.input_video,
        "output_video": task.output_video,
        "error": task.error_message,
        "progress": task.progress
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(webhook_url, json=payload)
            print(f"Webhook отправлен: {response.status_code}")
        except Exception as e:
            print(f"Ошибка отправки webhook: {e}")

# Использование в server_app.py
@app.post("/upload_with_webhook")
async def upload_with_webhook(
    file: UploadFile,
    webhook_url: str,
    **kwargs
):
    result = await upload_video(file, **kwargs)
    task_id = result['task_id']
    
    # Отправить webhook когда задача завершится
    # (можно добавить в фоновый обработчик)
    
    return result
```

## Пример 6: Docker (развертывание в контейнере)

```dockerfile
FROM python:3.10

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копирование кода
COPY . .

# Создание необходимых папок
RUN mkdir -p videos_input videos_output videos_temp server_logs queue_db

# Запуск сервера
CMD ["python", "run_server.py", "--host", "0.0.0.0", "--port", "8000"]
```

Запуск:
```bash
docker build -t media-cleaner .
docker run -p 8000:8000 -v $(pwd)/videos_output:/app/videos_output media-cleaner
```

## Пример 7: Cron job для периодической обработки

```bash
#!/bin/bash
# process_videos.sh - запускается каждый час

#!/bin/bash
cd /home/user/media_cleaner

# Обработать все видео в input папке
for video in videos_input/*.mp4; do
    if [ -f "$video" ]; then
        python client.py upload "$video" \
            --epsilon 0.12 \
            --audio средний \
            --wait \
            --download ./videos_output
    fi
done
```

Добавить в crontab:
```bash
0 * * * * /home/user/media_cleaner/process_videos.sh
```

## Пример 8: API интеграция с внешним сервисом

```python
import asyncio
import aiohttp
from datetime import datetime

class MediaCleanerIntegration:
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url
        self.api_key = api_key
    
    async def process_video(self, video_url: str, options: dict) -> str:
        """Скачать видео с URL, обработать и вернуть результат"""
        
        # Скачать видео
        async with aiohttp.ClientSession() as session:
            async with session.get(video_url) as resp:
                video_data = await resp.read()
        
        # Отправить на обработку
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field('file', video_data, 
                              filename='video.mp4')
            
            for key, value in options.items():
                form_data.add_field(key, str(value))
            
            async with session.post(
                f"{self.server_url}/upload",
                data=form_data
            ) as resp:
                result = await resp.json()
        
        return result['task_id']

# Использование
async def main():
    integration = MediaCleanerIntegration(
        "http://localhost:8000",
        "your-api-key"
    )
    
    task_id = await integration.process_video(
        "https://example.com/video.mp4",
        {"epsilon": 0.12, "audio_level": "средний"}
    )
    
    print(f"Task ID: {task_id}")

asyncio.run(main())
```

---

Эти примеры показывают различные способы интеграции Media Cleaner Server в ваши приложения.
