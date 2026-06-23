let selectedServer = null;
let refreshInterval;
let charts = {};

document.addEventListener('DOMContentLoaded', function() {
    loadServers();
    refreshInterval = setInterval(loadServers, 60000);
});

async function loadServers() {
    try {
        const response = await fetch('/api/servers');
        const data = await response.json();
        
        displayServers(data.servers);
        
        if (selectedServer) {
            const updatedServer = data.servers.find(s => s.id === selectedServer.id);
            if (updatedServer) {
                selectedServer = updatedServer;
                loadServerMetrics(selectedServer.name);
            } else {
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
                        ${server.name}
                    </h5>
                    <span class="badge ${onlineBadge}">${onlineText}</span>
                </div>
                <p class="card-text">
                    <small class="text-muted">
                        ${server.description || 'Нет описания'}
                    </small>
                </p>
                <div class="server-info">
                    <small class="text-muted">
                        <i class="fas fa-clock"></i>
                        Последний контакт: ${server.last_seen ? 
                            formatDateTime(server.last_seen) : 'Никогда'}
                    </small>
                </div>
            </div>
        </div>
    `;
    
    return card;
}

function isServerOnline(server) {
    if (!server.last_seen) return false;
    const lastSeen = new Date(server.last_seen);
    const now = new Date();
    const diffMinutes = (now - lastSeen) / (1000 * 60);
    return diffMinutes < 5;
}

function selectServer(server) {
    selectedServer = server;
    loadServers();
    loadServerMetrics(server.name);
}

function loadServerMetrics(serverName) {
    document.getElementById('metricsCharts').style.display = 'block';
    document.getElementById('noServerSelected').style.display = 'none';
    document.getElementById('selectedServerName').innerHTML = `Метрики для сервера ${serverName} (последние 24 часа)`;
    
    const timeRange = '24h';
    
    fetch(`/api/metrics/${serverName}?measurement=cpu&range=${timeRange}`)
        .then(response => response.json())
        .then(data => updateChart('cpu', data.metrics, 'usage_percent', 'Загрузка CPU (%)'))
        .catch(error => console.error('Error loading CPU metrics:', error));
    
    fetch(`/api/metrics/${serverName}?measurement=memory&range=${timeRange}`)
        .then(response => response.json())
        .then(data => updateChart('memory', data.metrics, 'usage_percent', 'Использование памяти (%)'))
        .catch(error => console.error('Error loading Memory metrics:', error));
    
    fetch(`/api/metrics/${serverName}?measurement=disk&range=${timeRange}`)
        .then(response => response.json())
        .then(data => {
            const driveData = data.metrics.filter(m => m.drive === 'C:');
            updateChart('disk', driveData, 'usage_percent', 'Использование диска C: (%)');
        })
        .catch(error => console.error('Error loading Disk metrics:', error));
    
    fetch(`/api/metrics/${serverName}?measurement=network&range=${timeRange}`)
        .then(response => response.json())
        .then(data => {
            updateChart('network', data.metrics, 'bytes_recv', 'Входящий трафик (bytes)');
        })
        .catch(error => console.error('Error loading Network metrics:', error));
}

function updateChart(chartId, metrics, field, label) {
    const canvas = document.getElementById(`${chartId}Chart`);
    if (!canvas) return;
    
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
                    x: {
                        title: { display: true, text: 'Время' }
                    },
                    y: {
                        title: { display: true, text: label }
                    }
                }
            }
        });
    }
}

function hideCharts() {
    document.getElementById('metricsCharts').style.display = 'none';
    document.getElementById('noServerSelected').style.display = 'block';
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