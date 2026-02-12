"""
Веб интерфейс для Media Cleaner Server
Flask приложение с красивым UI
"""

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_cors import CORS
import os
import requests
from pathlib import Path
import json
import logging
from datetime import datetime
import time
import threading

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
    template_folder='templates',
    static_folder='static'
)
CORS(app)

# Конфигурация
API_SERVER = os.getenv('API_SERVER', 'http://127.0.0.1:8000')
UPLOAD_FOLDER = Path('./web_uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB

# Хранилище активных сессий
active_sessions = {}


# ──── ГЛАВНАЯ СТРАНИЦА ────────────────────────────────────────────────────
@app.route('/')
def index():
    """Главная страница"""
    try:
        # Проверить доступность API
        response = requests.get(f"{API_SERVER}/health", timeout=5)
        server_status = "online" if response.status_code == 200 else "offline"
    except:
        server_status = "offline"
    
    return render_template('index.html', server_status=server_status)


# ──── ЗАГРУЗКА ВИДЕО ──────────────────────────────────────────────────────
@app.route('/upload', methods=['POST'])
def upload_video():
    """API endpoint для загрузки видео"""
    
    try:
        # Проверить файл
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Получить параметры обработки
        epsilon = float(request.form.get('epsilon', 0.12))
        video_strength = float(request.form.get('video_strength', 1.0))
        audio_level = request.form.get('audio_level', 'слабый')
        every_n_frames = int(request.form.get('every_n_frames', 10))
        user_id = request.form.get('user_id', 'web_user')
        
        # Валидация параметров
        if not (0.04 <= epsilon <= 0.20):
            return jsonify({'error': 'Epsilon должен быть между 0.04 и 0.20'}), 400
        
        if not (1.0 <= video_strength <= 2.0):
            return jsonify({'error': 'Strength должен быть между 1.0 и 2.0'}), 400
        
        if not (1 <= every_n_frames <= 30):
            return jsonify({'error': 'Frames должен быть между 1 и 30'}), 400
        
        # Сохранить файл временно
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        temp_filename = f"{unique_id}_{file.filename}"
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        file.save(temp_path)
        
        logger.info(f"📥 Файл загружен: {temp_filename}")
        
        # Отправить на API сервер
        with open(temp_path, 'rb') as f:
            files = {'file': (file.filename, f)}
            params = {
                'epsilon': epsilon,
                'video_strength': video_strength,
                'audio_level': audio_level,
                'every_n_frames': every_n_frames,
                'user_id': user_id,
            }
            
            response = requests.post(
                f"{API_SERVER}/upload",
                files=files,
                params=params,
                timeout=30
            )
        
        # Удалить временный файл
        try:
            os.remove(temp_path)
        except:
            pass
        
        if response.status_code != 200:
            return jsonify({'error': 'Ошибка при загрузке на сервер обработки'}), 500
        
        result = response.json()
        
        if result['status'] != 'success':
            return jsonify({'error': result.get('detail', 'Ошибка сервера')}), 500
        
        task_id = result['task_id']
        
        # Сохранить информацию о задаче в сессию
        active_sessions[task_id] = {
            'filename': file.filename,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'epsilon': epsilon,
            'video_strength': video_strength,
            'audio_level': audio_level,
        }
        
        return jsonify({
            'status': 'success',
            'task_id': task_id,
            'message': 'Видео загружено и добавлено в очередь'
        })
    
    except Exception as e:
        logger.error(f"[ERROR] Upload error: {e}")
        return jsonify({'error': str(e)}), 500


# ──── СТАТУС ЗАДАЧИ ──────────────────────────────────────────────────────
@app.route('/api/task/<task_id>')
def get_task_status(task_id):
    """Получить статус задачи"""
    
    try:
        response = requests.get(
            f"{API_SERVER}/task/{task_id}",
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Задача не найдена'}), 404
        
        result = response.json()
        task = result['task']
        
        return jsonify({
            'status': 'success',
            'task': task
        })
    
    except Exception as e:
        logger.error(f"[ERROR] Task status error: {e}")
        return jsonify({'error': str(e)}), 500


# ──── СКАЧАТЬ ВИДЕО ──────────────────────────────────────────────────────
@app.route('/api/download/<task_id>')
def download_video(task_id):
    """Скачать обработанное видео"""
    
    try:
        response = requests.get(
            f"{API_SERVER}/download/{task_id}",
            stream=True,
            timeout=30
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Видео не готово'}), 400
        
        # Отправить файл клиенту
        filename = f"protected_{task_id}.mp4"
        
        return send_file(
            response.raw,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
    
    except Exception as e:
        logger.error(f"[ERROR] Download error: {e}")
        return jsonify({'error': str(e)}), 500


# ──── ОТМЕНА ЗАДАЧИ ──────────────────────────────────────────────────────
@app.route('/api/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    """Отменить задачу"""
    
    try:
        response = requests.post(
            f"{API_SERVER}/cancel/{task_id}",
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Не удалось отменить задачу'}), 400
        
        return jsonify({'status': 'success', 'message': 'Задача отменена'})
    
    except Exception as e:
        logger.error(f"[ERROR] Cancel error: {e}")
        return jsonify({'error': str(e)}), 500


# ──── СТАТИСТИКА СЕРВЕРА ─────────────────────────────────────────────────
@app.route('/api/stats')
def get_stats():
    """Получить статистику сервера"""
    
    try:
        response = requests.get(
            f"{API_SERVER}/stats",
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Ошибка получения статистики'}), 500
        
        return response.json()
    
    except Exception as e:
        logger.error(f"[ERROR] Stats error: {e}")
        return jsonify({'error': str(e)}), 500


# ──── ПРОВЕРКА СЕРВЕРА ───────────────────────────────────────────────────
@app.route('/api/health')
def health():
    """Проверка здоровья API сервера"""
    
    try:
        response = requests.get(
            f"{API_SERVER}/health",
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify({'status': 'healthy', 'api': 'online'})
        else:
            return jsonify({'status': 'unhealthy', 'api': 'offline'}), 503
    
    except:
        return jsonify({'status': 'unhealthy', 'api': 'offline'}), 503


# ──── ОШИБКА 404 ─────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(error):
    """Обработка 404 ошибок"""
    return render_template('404.html'), 404


# ──── ОШИБКА 500 ─────────────────────────────────────────────────────────
@app.errorhandler(500)
def server_error(error):
    """Обработка 500 ошибок"""
    return jsonify({'error': 'Internal server error'}), 500


# ──── ЗАПУСК ───────────────────────────────────────────────────────────
def run_web_interface(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Запуск веб интерфейса"""
    
    logger.info(f"[API] Web interface running on http://{host}:{port}")
    logger.info(f"📡 API сервер: {API_SERVER}")
    
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == '__main__':
    # Можно запустить через: python web_interface.py
    import sys
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    run_web_interface(port=port, debug=False)
