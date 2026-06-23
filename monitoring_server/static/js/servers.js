let selectedServer = null;
let refreshInterval;
let charts = {};

// Загрузка при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('servers.js loaded');
    loadServers();
    // Обновляем список серверов каждые 60 секунд
    refreshInterval = setInterval(loadServers, 60000);
});

async function loadServers() {
    try {
        console.log('Loading servers...');
        const response = await fetch('/api/servers');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Received servers:', data.servers);
        
        displayServers(data.servers);
        
        // Если выбран сервер, обновляем его статус и загружаем графики
        if (selectedServer) {
            // Проверяем, есть ли сервер в новом списке
            const updatedServer = data.servers.find(s => s.id === selectedServer.id);
            if (updatedServer) {
                selectedServer = updatedServer;
                loadServerMetrics(selectedServer.name);
            } else {
                // Если сервер удалён, сбрасываем выбор
                selectedServer = null;
                hideCharts();
            }
        }
        
    } catch (error) {
        console.error('Error loading servers:', error);
        showError('Ошибка загрузки списка серверов');
    }
}

function displayServers(servers) {
    const container = document.getElementById('serversContainer');
    if (!container) {
        console.error('serversContainer element not found');
        return;
    }
    container.innerHTML = '';
    
    if (servers.length === 0) {
        container.innerHTML = '<div class="col-12"><p class="text-muted">Нет зарегистрированных серверов</p></div>';
        return;
    }
    
    servers.forEach(server => {
        const isOnline = isServerOnline(server);
        const card = createServerCard(server, isOnline);
        container.appendChild(card);
    });
}

function createServerCard(server, isOnline) {
    const card = document.createElement('div');
    card.className = 'col-md-3 mb-3';
    card.style.cursor = 'pointer';
    
    const isSelected = selectedServer && selectedServer.id === server.id;
    const borderClass = isSelected ? 'border-primary border-2' : '';
    const onlineClass = isOnline ? 'text-success' : 'text-danger';
    const onlineBadge = isOnline ? 'bg-success' : 'bg-danger';
    const onlineText = isOnline ? 'Online' : 'Offline';
    
    card.innerHTML = `
        <div class="card ${borderClass} server-card" 
             onclick="selectServer(${JSON.stringify(server).replace(/"/g, '&quot;')})">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <h5 class="card-title">
                        <i class="fas fa-server ${onlineClass}"></i>
                        ${escapeHtml(server.name)}
                    </h5>
                    <span class="badge ${onlineBadge}">${onlineText}</span>
                </div>
                <p class="card-text">
                    <small class="text-muted">
                        ${escapeHtml(server.description || 'Нет описания')}
                    </small>
                </p>
                <div class="server-info">
                    <small class="text-muted">
                        <i class="fas fa-clock"></i>
                        Последний контакт: ${server.last_seen ? formatDateTime(server.last_seen) : 'Никогда'}
                    </small>
                </div>
            </div>
        </div>
    `;
    
    return card;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function isServerOnline(server) {
    if (!server.last_seen) return false;
    const lastSeen = new Date(server.last_seen);
    const now = new Date();
    const diffMinutes = (now - lastSeen) / (1000 * 60);
    return diffMinutes < 5; // 5 минут
}

function selectServer(server) {
    console.log('Selected server:', server);
    selectedServer = server;
    // Перерисовываем список для выделения выбранного
    loadServers(); // это вызовет перерисовку
    // Загружаем метрики для выбранного сервера
    loadServerMetrics(server.name);
}

function loadServerMetrics(serverName) {
    // Показываем контейнер с графиками, скрываем сообщение
    const metricsCharts = document.getElementById('metricsCharts');
    const noServerSelected = document.getElementById('noServerSelected');
    const selectedServerName = document.getElementById('selectedServerName');
    
    if (metricsCharts) metricsCharts.style.display = 'block';
    if (noServerSelected) noServerSelected.style.display = 'none';
    if (selectedServerName) selectedServerName.innerHTML = `Метрики для сервера ${serverName} (последние 24 часа)`;
    
    const timeRange = '24h';
    
    // Загружаем CPU
    fetch(`/api/metrics/${serverName}?measurement=cpu&range=${timeRange}`)
        .then(response => response.json())
        .then(data => updateChart('cpu', data.metrics, 'usage_percent', 'Загрузка CPU (%)'))
        .catch(error => console.error('Error loading CPU metrics:', error));
    
    // Загружаем Memory
    fetch(`/api/metrics/${serverName}?measurement=memory&range=${timeRange}`)
        .then(response => response.json())
        .then(data => updateChart('memory', data.metrics, 'usage_percent', 'Использование памяти (%)'))
        .catch(error => console.error('Error loading Memory metrics:', error));
    
    // Загружаем Disk (первый диск, например C:)
    fetch(`/api/metrics/${serverName}?measurement=disk&range=${timeRange}`)
        .then(response => response.json())
        .then(data => {
            const driveData = data.metrics.filter(m => m.drive === 'C:');
            updateChart('disk', driveData, 'usage_percent', 'Использование диска C: (%)');
        })
        .catch(error => console.error('Error loading Disk metrics:', error));
    
    // Загружаем Network
    fetch(`/api/metrics/${serverName}?measurement=network&range=${timeRange}`)
        .then(response => response.json())
        .then(data => {
            updateChart('network', data.metrics, 'bytes_recv', 'Входящий трафик (bytes)');
        })
        .catch(error => console.error('Error loading Network metrics:', error));
}

function updateChart(chartId, metrics, field, label) {
    const canvas = document.getElementById(`${chartId}Chart`);
    if (!canvas) {
        console.warn(`Canvas element ${chartId}Chart not found`);
        return;
    }
    
    const sorted = [...metrics].sort((a, b) => new Date(a.time) - new Date(b.time));
    const timestamps = sorted.map(m => new Date(m.time).toLocaleString());
    const values = sorted.map(m => m[field]);
    
    if (charts[chartId]) {
        charts[chartId].data.labels = timestamps;
        charts[chartId].data.datasets[0].data = values;
        charts[chartId].update();
    } else {
        const ctx = canvas.getContext('2d');
        charts[chartId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: label,
                    data: values,
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    x: { title: { display: true, text: 'Время' } },
                    y: { title: { display: true, text: label } }
                }
            }
        });
    }
}

function hideCharts() {
    const metricsCharts = document.getElementById('metricsCharts');
    const noServerSelected = document.getElementById('noServerSelected');
    if (metricsCharts) metricsCharts.style.display = 'none';
    if (noServerSelected) noServerSelected.style.display = 'block';
    
    for (let key in charts) {
        if (charts[key]) {
            charts[key].destroy();
            delete charts[key];
        }
    }
}

function formatDateTime(dateString) {
    if (!dateString) return 'Никогда';
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU');
}

function refreshServers() {
    loadServers();
    showInfo('Список серверов обновлен');
}

window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

function showError(message) {
    alert('Ошибка: ' + message);
}

function showInfo(message) {
    console.log('Info: ' + message);
}