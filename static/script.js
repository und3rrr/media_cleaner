/**
 * ═══════════════════════════════════════════════════════════════════════════
 * MEDIA CLEANER - ВЕБ ИНТЕРФЕЙС (JavaScript)
 * ═══════════════════════════════════════════════════════════════════════════
 */

// ═════════════════════════════════════════════════════════════════════════
// КОНФИГУРАЦИЯ
// ═════════════════════════════════════════════════════════════════════════

const API_SERVER = 'http://127.0.0.1:8000';

// ═════════════════════════════════════════════════════════════════════════
// ПЕРЕМЕННЫЕ СОСТОЯНИЯ
// ═════════════════════════════════════════════════════════════════════════

let state = {
    selectedFile: null,
    currentTaskId: null,
    isProcessing: false,
    statusCheckInterval: null,
    pollCount: 0,
    startTime: null,
};

// ═════════════════════════════════════════════════════════════════════════
// DOM ЭЛЕМЕНТЫ
// ═════════════════════════════════════════════════════════════════════════

const DOM = {
    // Файл
    dropZone: document.getElementById('dropZone'),
    fileInput: document.getElementById('fileInput'),
    fileInfo: document.getElementById('fileInfo'),
    fileName: document.getElementById('fileName'),
    fileSize: document.getElementById('fileSize'),
    clearFile: document.getElementById('clearFile'),
    
    // Параметры
    epsilon: document.getElementById('epsilon'),
    epsilonValue: document.getElementById('epsilonValue'),
    audioLevel: document.getElementById('audioLevel'),
    everyNFrames: document.getElementById('everyNFrames'),
    everyNFramesValue: document.getElementById('everyNFramesValue'),
    videoStrength: document.getElementById('videoStrength'),
    videoStrengthValue: document.getElementById('videoStrengthValue'),
    userId: document.getElementById('userId'),
    
    // Кнопки
    processBtn: document.getElementById('processBtn'),
    cancelBtn: document.getElementById('cancelBtn'),
    downloadBtn: document.getElementById('downloadBtn'),
    
    // Статус
    noTask: document.getElementById('noTask'),
    taskStatus: document.getElementById('taskStatus'),
    statusBadge: document.getElementById('statusBadge'),
    taskIdDisplay: document.getElementById('taskIdDisplay'),
    statusDetails: document.getElementById('statusDetails'),
    
    // Прогресс
    uploadProgress: document.getElementById('uploadProgress'),
    uploadProgressBar: document.getElementById('uploadProgressBar'),
    uploadProgressText: document.getElementById('uploadProgressText'),
    taskProgress: document.getElementById('taskProgress'),
    progressLabel: document.getElementById('progressLabel'),
    progressPercent: document.getElementById('progressPercent'),
    
    // Консоль
    console: document.getElementById('console'),
    
    // Сервер статус
    serverIndicator: document.getElementById('serverIndicator'),
    serverText: document.getElementById('serverText'),
};

// ═════════════════════════════════════════════════════════════════════════
// PAGE VISIBILITY API - PAUSE/RESUME POLLING
// ═════════════════════════════════════════════════════════════════════════

// Автоматически паузировать polling когда вкладка скрыта
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Вкладка скрыта - остановить polling
        if (state.statusCheckInterval) {
            clearInterval(state.statusCheckInterval);
            state.statusCheckInterval = null;
        }
    } else {
        // Вкладка видима снова - перезапустить polling если есть активная задача
        if (state.isProcessing && state.currentTaskId && !state.statusCheckInterval) {
            startStatusPolling();
        }
    }
});

// ═════════════════════════════════════════════════════════════════════════
// ИНИЦИАЛИЗАЦИЯ
// ═════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    console.log('🔧 [DEBUG] DOMContentLoaded triggered');
    console.log('🔧 [DEBUG] setupFileHandlers...');
    setupFileHandlers();
    console.log('🔧 [DEBUG] setupParameterHandlers...');
    setupParameterHandlers();
    console.log('🔧 [DEBUG] setupButtonHandlers...');
    setupButtonHandlers();
    console.log('🔧 [DEBUG] checkServerStatus...');
    checkServerStatus();
    console.log('🔧 [DEBUG] Interface initialized successfully');
    addConsoleLog('✨ Интерфейс загружен', 'info');
});

// ═════════════════════════════════════════════════════════════════════════
// ОБРАБОТЧИК ФАЙЛА
// ═════════════════════════════════════════════════════════════════════════

function setupFileHandlers() {
    // Клик на зону перетаскивания (и её содержимое)
    DOM.dropZone.addEventListener('click', (e) => {
        e.stopPropagation();
        DOM.fileInput.click();
    });
    
    // Если у есть drop-content, добавим обработчик и на него
    const dropContent = document.querySelector('.drop-content');
    if (dropContent) {
        dropContent.addEventListener('click', (e) => {
            e.stopPropagation();
            DOM.fileInput.click();
        });
    }

    // Выбор файла через input
    DOM.fileInput.addEventListener('change', (e) => {
        handleFileSelect(e.target.files[0]);
    });

    // Перетаскивание файла
    DOM.dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        DOM.dropZone.classList.add('drag-over');
    });

    DOM.dropZone.addEventListener('dragleave', (e) => {
        e.stopPropagation();
        DOM.dropZone.classList.remove('drag-over');
    });

    DOM.dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        DOM.dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    // Очистить файл
    DOM.clearFile.addEventListener('click', (e) => {
        e.stopPropagation();
        clearFile();
    });
}

function handleFileSelect(file) {
    if (!file) return;

    // Проверка типа файла
    if (!file.type.startsWith('video/')) {
        alert('⚠️ Пожалуйста, выберите видео файл');
        return;
    }

    // Проверка размера (макс. 2GB)
    const MAX_SIZE = 2 * 1024 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
        alert('⚠️ Файл слишком большой (макс. 2GB)');
        return;
    }

    state.selectedFile = file;
    updateFileInfo();
    updateProcessButtonState();
    addConsoleLog(`📁 Файл выбран: ${file.name} (${formatFileSize(file.size)})`, 'success');
}

function clearFile() {
    state.selectedFile = null;
    DOM.fileInput.value = '';
    DOM.fileInfo.style.display = 'none';
    DOM.dropZone.style.display = 'flex';
    
    // Очистить polling если активен
    if (state.statusCheckInterval) {
        clearInterval(state.statusCheckInterval);
        state.statusCheckInterval = null;
    }
    
    // Очистить состояние задачи
    state.isProcessing = false;
    state.currentTaskId = null;
    
    updateProcessButtonState();
    addConsoleLog('🗑️ Файл удален', 'warning');
}

function updateFileInfo() {
    DOM.fileName.textContent = state.selectedFile.name;
    DOM.fileSize.textContent = formatFileSize(state.selectedFile.size);
    DOM.fileInfo.style.display = 'block';
    DOM.dropZone.style.display = 'none';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
}

// ═════════════════════════════════════════════════════════════════════════
// ПАРАМЕТРЫ
// ═════════════════════════════════════════════════════════════════════════

function setupParameterHandlers() {
    // Синхронизация слайдеров с числовыми вводами
    bindSliderToInput(DOM.epsilon, DOM.epsilonValue);
    bindSliderToInput(DOM.everyNFrames, DOM.everyNFramesValue);
    bindSliderToInput(DOM.videoStrength, DOM.videoStrengthValue);
}

function bindSliderToInput(slider, input) {
    // Слайдер -> инпут (в реальном времени)
    slider.addEventListener('input', (e) => {
        const value = parseFloat(e.target.value);
        input.value = value;
        updateSliderBackground(slider);
    });

    // Инпут -> слайдер (при изменении)
    input.addEventListener('input', (e) => {
        let value = parseFloat(e.target.value);
        
        // Валидация границ
        const min = parseFloat(slider.min);
        const max = parseFloat(slider.max);
        value = Math.max(min, Math.min(max, value));
        
        input.value = value;
        slider.value = value;
        updateSliderBackground(slider);
    });

    // Инпут -> слайдер (при завершении ввода)
    input.addEventListener('change', (e) => {
        let value = parseFloat(e.target.value);
        
        // Валидация границ
        const min = parseFloat(slider.min);
        const max = parseFloat(slider.max);
        value = Math.max(min, Math.min(max, value));
        
        input.value = value;
        slider.value = value;
        updateSliderBackground(slider);
    });

    // Инициализация фона слайдера
    updateSliderBackground(slider);
}

function updateSliderBackground(slider) {
    const value = (slider.value - slider.min) / (slider.max - slider.min) * 100;
    slider.style.setProperty('--value', value + '%');
}

// ═════════════════════════════════════════════════════════════════════════
// КНОПКИ И СОБЫТИЯ
// ═════════════════════════════════════════════════════════════════════════

function setupButtonHandlers() {
    DOM.processBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        startProcessing();
    });
    DOM.cancelBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        cancelProcessing();
    });
    DOM.downloadBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        downloadVideo();
    });
}

function updateProcessButtonState() {
    const isEnabled = state.selectedFile && !state.isProcessing;
    DOM.processBtn.disabled = !isEnabled;
    DOM.processBtn.textContent = state.isProcessing 
        ? '⏳ Обработка...'
        : '🚀 Начать обработку';
}

// ═════════════════════════════════════════════════════════════════════════
// ЗАГРУЗКА И ОБРАБОТКА
// ═════════════════════════════════════════════════════════════════════════

async function startProcessing() {
    if (!state.selectedFile || state.isProcessing) return;

    // Очистить старый интервал polling если существует
    if (state.statusCheckInterval) {
        clearInterval(state.statusCheckInterval);
        state.statusCheckInterval = null;
    }

    state.isProcessing = true;
    updateProcessButtonState();
    clearConsole();
    addConsoleLog('🚀 Начало загрузки видео...', 'info');

    const formData = new FormData();
    formData.append('file', state.selectedFile);
    formData.append('epsilon', DOM.epsilon.value);
    formData.append('video_strength', DOM.videoStrength.value);
    formData.append('audio_level', DOM.audioLevel.value);
    formData.append('every_n_frames', DOM.everyNFrames.value);
    formData.append('user_id', DOM.userId.value || 'web_user');

    try {
        // Показать прогресс загрузки
        showUploadProgress();

        const xhr = new XMLHttpRequest();

        // Отслеживание прогресса загрузки
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                DOM.uploadProgressBar.style.width = percentComplete + '%';
                DOM.uploadProgressText.textContent = `Загрузка: ${percentComplete}%`;
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                
                if (response.status === 'success') {
                    state.currentTaskId = response.task_id;
                    state.startTime = Date.now();
                    
                    // Логирование в localStorage
                    addVideoLog(
                        DOM.userId.value || 'web_user',
                        state.selectedFile.name,
                        (state.selectedFile.size / 1024 / 1024).toFixed(2) + ' MB',
                        {
                            epsilon: DOM.epsilon.value,
                            audioLevel: DOM.audioLevel.value,
                            everyNFrames: DOM.everyNFrames.value,
                            videoStrength: DOM.videoStrength.value
                        },
                        'ЗАГРУЖЕНО',
                        0
                    );
                    
                    addConsoleLog(`✅ Видео загружено! ID: ${response.task_id}`, 'success');
                    addConsoleLog('⏳ Видео добавлено в очередь обработки...', 'info');
                    
                    hideUploadProgress();
                    showTaskStatus();
                    startStatusPolling();
                } else {
                    throw new Error(response.error || 'Ошибка загрузки');
                }
            } else {
                throw new Error(`HTTP ${xhr.status}`);
            }
        });

        xhr.addEventListener('error', () => {
            throw new Error('Ошибка сети при загрузке');
        });

        xhr.open('POST', '/upload');
        xhr.send(formData);

    } catch (error) {
        addConsoleLog(`❌ Ошибка: ${error.message}`, 'error');
        state.isProcessing = false;
        hideUploadProgress();
        updateProcessButtonState();
    }
}

function showUploadProgress() {
    DOM.uploadProgress.style.display = 'block';
    DOM.uploadProgressBar.style.width = '0%';
    DOM.uploadProgressText.textContent = 'Загрузка: 0%';
}

function hideUploadProgress() {
    DOM.uploadProgress.style.display = 'none';
}

function showTaskStatus() {
    DOM.noTask.style.display = 'none';
    DOM.taskStatus.style.display = 'block';
    DOM.taskIdDisplay.textContent = `ID: ${state.currentTaskId.substring(0, 8)}...`;
    updateBadge('pending', 'ОЖИДАНИЕ');
}

// ═════════════════════════════════════════════════════════════════════════
// СТАТУС ЗАДАЧИ И ОПРОСЫ
// ═════════════════════════════════════════════════════════════════════════

function startStatusPolling() {
    // Если polling уже активен, не запускаем еще один
    if (state.statusCheckInterval) {
        return;
    }

    // Первая проверка сразу
    checkTaskStatus();

    // Затем каждые 2 секунды
    state.statusCheckInterval = setInterval(() => {
        if (!state.isProcessing && state.currentTaskId) {
            clearInterval(state.statusCheckInterval);
            state.statusCheckInterval = null;
            return;
        }
        checkTaskStatus();
    }, 2000);
}

async function checkTaskStatus() {
    if (!state.currentTaskId) return;

    try {
        const response = await fetch(`/api/task/${state.currentTaskId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        const task = data.task;

        // Обновить статус
        updateTaskDisplay(task);

        // Если завершено или ошибка, остановить опрос
        if (['completed', 'failed', 'cancelled'].includes(task.status)) {
            state.isProcessing = false;
            if (state.statusCheckInterval) {
                clearInterval(state.statusCheckInterval);
                state.statusCheckInterval = null;
            }
            updateProcessButtonState();
        }

    } catch (error) {
        console.error('Ошибка проверки статуса:', error);
        // При ошибке сети - остановить polling на некоторое время
        if (state.statusCheckInterval) {
            clearInterval(state.statusCheckInterval);
            state.statusCheckInterval = null;
        }
    }
}

function updateTaskDisplay(task) {
    const { status, progress, total_frames, processed_frames, message } = task;

    // Обновить бадж статуса
    const statusText = {
        'pending': 'ОЖИДАНИЕ',
        'processing': 'ОБРАБОТКА',
        'completed': '✅ ЗАВЕРШЕНО',
        'failed': '❌ ОШИБКА',
        'cancelled': '⛔ ОТМЕНЕНО',
    };
    updateBadge(status, statusText[status] || status.toUpperCase());

    // Обновить прогресс бар - прогресс может быть 0-1 или 0-100
    let progressPercent = 0;
    if (progress !== undefined && progress !== null) {
        // Если прогресс > 1, то он в процентах
        if (progress > 1) {
            progressPercent = Math.min(100, Math.round(progress));
        } else {
            // Если прогресс 0-1, то это доля
            progressPercent = Math.round(progress * 100);
        }
    }
    // Если есть frames данные, использовать их для вычисления прогресса
    if (total_frames && total_frames > 0) {
        progressPercent = Math.round(((processed_frames || 0) / total_frames) * 100);
    }
    
    DOM.taskProgress.style.width = progressPercent + '%';
    DOM.progressPercent.textContent = progressPercent + '%';

    // Обновить текст прогресса
    if (status === 'processing') {
        DOM.progressLabel.textContent = `Обрабатывается: ${processed_frames || 0} / ${total_frames || '?'} кадров`;
    } else if (status === 'completed') {
        DOM.progressLabel.textContent = 'Обработка завершена!';
    } else if (status === 'failed') {
        DOM.progressLabel.textContent = 'Обработка завершена с ошибкой';
    } else {
        DOM.progressLabel.textContent = 'Ожидание в очереди...';
    }

    // Обновить детали статуса
    updateStatusDetails(task);

    // Показать/скрыть кнопки
    DOM.cancelBtn.style.display = 
        (status === 'pending' || status === 'processing') ? 'block' : 'none';
    DOM.downloadBtn.style.display = 
        status === 'completed' ? 'block' : 'none';

    // Добавить логи при смене статуса
    const logMessage = task.last_log_message;
    if (logMessage && !state.lastLogMessage) {
        addConsoleLog(logMessage, 'info');
        state.lastLogMessage = logMessage;
    }
    if (logMessage && logMessage !== state.lastLogMessage) {
        addConsoleLog(logMessage, 'info');
        state.lastLogMessage = logMessage;
    }

    // Логи для статусов
    if (status === 'completed') {
        addConsoleLog('🎉 Видео готово к скачиванию!', 'success');
        
        // Обновить лог с финальным временем обработки
        if (state.startTime) {
            const duration = Date.now() - state.startTime;
            const logsData = JSON.parse(localStorage.getItem('mediaCleanerLogs') || '[]');
            
            // Обновить последний лог (самый первый в массиве)
            if (logsData.length > 0) {
                logsData[0].status = 'ЗАВЕРШЕНО';
                logsData[0].duration = duration;
                localStorage.setItem('mediaCleanerLogs', JSON.stringify(logsData));
                loadLogs(); // Обновить таблицу логов
            }
        }
    } else if (status === 'failed') {
        addConsoleLog('❌ Ошибка обработки: ' + (message || 'Неизвестная ошибка'), 'error');
        
        // Обновить лог с ошибкой
        if (state.startTime) {
            const duration = Date.now() - state.startTime;
            const logsData = JSON.parse(localStorage.getItem('mediaCleanerLogs') || '[]');
            
            if (logsData.length > 0) {
                logsData[0].status = 'ОШИБКА';
                logsData[0].duration = duration;
                localStorage.setItem('mediaCleanerLogs', JSON.stringify(logsData));
                loadLogs();
            }
        }
    }
}

function updateStatusDetails(task) {
    let html = '';
    
    // Статус
    const statusText = {
        'pending': '⏳ Ожидание',
        'processing': '⚙️ Обработка',
        'completed': '✅ Завершено',
        'failed': '❌ Ошибка',
        'cancelled': '⛔ Отменено',
    };
    html += `<p><strong>Статус:</strong> ${statusText[task.status] || task.status}</p>`;

    // Время обработки
    if (task.processing_started_at && task.status === 'processing') {
        html += `<p><strong>Обработка:</strong> идет...`;
    }

    // Прогресс
    if (task.total_frames) {
        const percent = Math.round((task.processed_frames / task.total_frames) * 100);
        html += `<p><strong>Кадры:</strong> ${task.processed_frames || 0}/${task.total_frames} (${percent}%)</p>`;
    }

    // Параметры обработки
    html += `<p><strong>Параметры:</strong></p>`;
    html += `<p style="margin-left: 12px;">
        • Epsilon: ${task.epsilon || 'N/A'}<br>
        • Audio Level: ${task.audio_level || 'N/A'}<br>
        • Strength: ${task.video_strength || 'N/A'}<br>
        • Every N Frames: ${task.every_n_frames || 'N/A'}
    </p>`;

    // Сообщение об ошибке
    if (task.message) {
        html += `<p style="color: #fca5a5;"><strong>Сообщение:</strong> ${task.message}</p>`;
    }

    DOM.statusDetails.innerHTML = html;
}

function updateBadge(status, text) {
    DOM.statusBadge.className = `badge ${status}`;
    DOM.statusBadge.textContent = text;
}

// ═════════════════════════════════════════════════════════════════════════
// ОТМЕНА И СКАЧИВАНИЕ
// ═════════════════════════════════════════════════════════════════════════

async function cancelProcessing() {
    if (!state.currentTaskId || !confirm('Вы уверены?')) return;

    try {
        // Сразу остановить polling
        if (state.statusCheckInterval) {
            clearInterval(state.statusCheckInterval);
            state.statusCheckInterval = null;
        }
        state.isProcessing = false;
        
        const response = await fetch(`/api/cancel/${state.currentTaskId}`, {
            method: 'POST'
        });

        if (response.ok) {
            addConsoleLog('⛔ Обработка отменена', 'warning');
            updateProcessButtonState();
        } else {
            addConsoleLog('❌ Ошибка при отмене', 'error');
        }
    } catch (error) {
        addConsoleLog('❌ Ошибка отмены: ' + error.message, 'error');
    }
}

async function downloadVideo() {
    if (!state.currentTaskId) return;

    addConsoleLog('📥 Начало скачивания...', 'info');

    try {
        const response = await fetch(`/api/download/${state.currentTaskId}`);
        
        if (!response.ok) {
            throw new Error('Видео не готово');
        }

        // Создать blob и скачать
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `protected_${state.currentTaskId.substring(0, 8)}.mp4`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        addConsoleLog('✅ Видео скачано!', 'success');

    } catch (error) {
        addConsoleLog('❌ Ошибка скачивания: ' + error.message, 'error');
    }
}

// ═════════════════════════════════════════════════════════════════════════
// КОНСОЛЬ ЛОГОВ
// ═════════════════════════════════════════════════════════════════════════

function addConsoleLog(message, type = 'info') {
    const time = new Date().toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });

    const line = document.createElement('div');
    line.className = 'console-line';
    line.innerHTML = `
        <span class="console-time">[${time}]</span>
        <span class="console-text ${type}">${escapeHtml(message)}</span>
    `;

    DOM.console.appendChild(line);

    // Автоскролл к последнему логу
    DOM.console.scrollTop = DOM.console.scrollHeight;

    // Лимит логов (держать только последние 100)
    while (DOM.console.children.length > 100) {
        DOM.console.removeChild(DOM.console.firstChild);
    }
}

function clearConsole() {
    DOM.console.innerHTML = '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ═════════════════════════════════════════════════════════════════════════
// ПРОВЕРКА СЕРВЕРА
// ═════════════════════════════════════════════════════════════════════════

async function checkServerStatus() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();

        if (data.status === 'healthy') {
            updateServerStatus(true);
        } else {
            updateServerStatus(false);
        }
    } catch (error) {
        updateServerStatus(false);
    }

    // Проверять каждые 30 секунд
    setInterval(checkServerStatus, 30000);
}

function updateServerStatus(isOnline) {
    if (isOnline) {
        DOM.serverIndicator.className = 'status-indicator online';
        DOM.serverText.textContent = '🟢 Сервер online';
    } else {
        DOM.serverIndicator.className = 'status-indicator offline';
        DOM.serverText.textContent = '🔴 Сервер offline';
    }
}

// ═════════════════════════════════════════════════════════════════════════
// УТИЛИТЫ
// ═════════════════════════════════════════════════════════════════════════

// Обработчик ошибок глобально
window.addEventListener('error', (e) => {
    console.error('Глобальная ошибка:', e.error);
    addConsoleLog('⚠️ Ошибка: ' + e.error?.message, 'error');
});

// Предупреждение перед закрытием если идет обработка
window.addEventListener('beforeunload', (e) => {
    if (state.isProcessing) {
        e.preventDefault();
        e.returnValue = '';
        return '';
    }
});

// ═════════════════════════════════════════════════════════════════════════
// УПРАВЛЕНИЕ ВКЛАДКАМИ
// ═════════════════════════════════════════════════════════════════════════

function setupTabHandlers() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            
            // Скрыть все вкладки
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(tc => tc.classList.remove('active'));
            
            // Показать выбранную вкладку
            btn.classList.add('active');
            const tabContent = document.getElementById(tabName + '-tab');
            if (tabContent) {
                tabContent.classList.add('active');
            }
            
            // Остановить polling если переходим не на вкладку processor
            if (tabName !== 'processor') {
                if (state.statusCheckInterval) {
                    clearInterval(state.statusCheckInterval);
                    state.statusCheckInterval = null;
                }
            } else if (tabName === 'processor' && state.isProcessing && state.currentTaskId) {
                // Перезапустить polling если возвращаемся на вкладку processor с активной задачей
                startStatusPolling();
            }
            
            // Обновить логи при открытии вкладки
            if (tabName === 'logs') {
                loadLogs();
            }
        });
    });
}

// Загрузить логи с localStorage
function loadLogs() {
    const logsData = JSON.parse(localStorage.getItem('mediaCleanerLogs') || '[]');
    const tbody = document.getElementById('logsTableBody');
    
    if (logsData.length === 0) {
        tbody.innerHTML = `<tr>
            <td colspan="7" style="text-align: center; padding: 20px; color: #888;">
                Нет записей в логах. Начните обработку видео!
            </td>
        </tr>`;
        return;
    }
    
    tbody.innerHTML = logsData.map(log => `<tr>
        <td>${new Date(log.timestamp).toLocaleString('ru-RU')}</td>
        <td>${log.user || 'Неизвестный'}</td>
        <td title="${log.filename}"><strong>${log.filename.split('/').pop().substring(0, 30)}...</strong></td>
        <td>${log.filesize}</td>
        <td>ε=${log.epsilon}, a=${log.audioLevel}, f=${log.everyNFrames}, s=${log.videoStrength}</td>
        <td><span class="badge-${log.status.toLowerCase()}">${log.status}</span></td>
        <td>${log.duration}ms</td>
    </tr>`).join('');
}

// Добавить логирующее событие при обработке видео
function addVideoLog(user, filename, filesize, params, status, duration) {
    const logsData = JSON.parse(localStorage.getItem('mediaCleanerLogs') || '[]');
    
    logsData.unshift({
        timestamp: new Date().toISOString(),
        user: user || 'Неизвестный',
        filename: filename,
        filesize: filesize,
        epsilon: params.epsilon,
        audioLevel: params.audioLevel,
        everyNFrames: params.everyNFrames,
        videoStrength: params.videoStrength,
        status: status,
        duration: duration
    });
    
    // Сохранить только последние 50 записей
    logsData.splice(50);
    localStorage.setItem('mediaCleanerLogs', JSON.stringify(logsData));
}

// Очистить логи
function clearLogs() {
    if (confirm('Вы уверены? Это удалит все логи обработки!')) {
        localStorage.removeItem('mediaCleanerLogs');
        loadLogs();
        addConsoleLog('📋 Логи очищены', 'info');
    }
}

// Обновить логи
function refreshLogs() {
    loadLogs();
    addConsoleLog('🔄 Логи обновлены', 'info');
}

// Обработчики кнопок логов
document.addEventListener('DOMContentLoaded', () => {
    setupTabHandlers();
    
    const refreshBtn = document.getElementById('refreshLogsBtn');
    const clearBtn = document.getElementById('clearLogsBtn');
    
    if (refreshBtn) refreshBtn.addEventListener('click', refreshLogs);
    if (clearBtn) clearBtn.addEventListener('click', clearLogs);

    // Метаданные
    setupMetadataHandlers();
});

// ═════════════════════════════════════════════════════════════════════════
// УДАЛЕНИЕ МЕТАДАННЫХ
// ═════════════════════════════════════════════════════════════════════════

function setupMetadataHandlers() {
    const dropZone = document.getElementById('metadataDropZone');
    const fileInput = document.getElementById('metadataFileInput');
    const fileInfo = document.getElementById('metadataFileInfo');
    const fileName = document.getElementById('metadataFileName');
    const fileSize = document.getElementById('metadataFileSize');
    const stripBtn = document.getElementById('stripMetadataBtn');
    const downloadBtn = document.getElementById('metadataDownloadBtn');
    const progress = document.getElementById('metadataProgress');
    const progressBar = document.getElementById('metadataProgressBar');
    const progressText = document.getElementById('metadataProgressText');

    let selectedFile = null;
    let taskId = null;

    // Drop zone events
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#4CAF50';
        dropZone.style.backgroundColor = 'rgba(76, 175, 80, 0.1)';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = '#ddd';
        dropZone.style.backgroundColor = 'transparent';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#ddd';
        dropZone.style.backgroundColor = 'transparent';
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleMetadataFile(files[0]);
        }
    });

    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleMetadataFile(e.target.files[0]);
        }
    });

    function handleMetadataFile(file) {
        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = (file.size / 1024 / 1024).toFixed(2) + ' MB';
        fileInfo.style.display = 'block';
        stripBtn.style.display = 'block';
    }

    stripBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        const formData = new FormData();
        formData.append('file', selectedFile);

        stripBtn.disabled = true;
        progress.style.display = 'block';

        try {
            const response = await fetch(`${API_SERVER}/strip-metadata`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            taskId = result.task_id;

            // Poll for progress
            const pollInterval = setInterval(async () => {
                try {
                    const statusResp = await fetch(`${API_SERVER}/task/${taskId}`);
                    const statusData = await statusResp.json();
                    const task = statusData.task;

                    const progressPercent = Math.min(100, Math.round((task.progress || 0)));
                    progressBar.style.width = progressPercent + '%';
                    progressText.textContent = `Обработка: ${progressPercent}%`;

                    if (task.status === 'completed') {
                        clearInterval(pollInterval);
                        progress.style.display = 'none';
                        downloadBtn.style.display = 'block';
                        downloadBtn.onclick = () => downloadFile(taskId, 'metadata');
                    } else if (task.status === 'failed') {
                        clearInterval(pollInterval);
                        progress.style.display = 'none';
                        stripBtn.disabled = false;
                        alert('Ошибка обработки');
                    }
                } catch (err) {
                    console.error('Ошибка статуса:', err);
                }
            }, 1000);
        } catch (error) {
            alert('Ошибка загрузки: ' + error.message);
            stripBtn.disabled = false;
        }
    });
}

function downloadFile(taskId, type) {
    const endpoint = type === 'metadata' ? 'strip-metadata' : 'compress';
    window.location.href = `${API_SERVER}/download/${taskId}`;
}

