// Обновление данных каждые 30 секунд
setInterval(loadDashboardData, 30000);

// Загрузка данных при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
});

async function loadDashboardData() {
    try {
        await loadServers();
        await loadAlerts();
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

async function loadServers() {
    const response = await fetch('/api/servers');
    const data = await response.json();
    
    const serversList = document.getElementById('servers-list');
    serversList.innerHTML = '';
    
    data.servers.forEach(server => {
        // Проверяем, был ли контакт в последние 5 минут (300000 мс)
        const isOnline = server.last_seen && 
            (new Date() - new Date(server.last_seen)) < 300000; // 5 минут
        
        const serverCard = `
            <div class="col-md-4 mb-3">
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <h5 class="card-title">
                                <i class="fas fa-server ${isOnline ? 'server-status-online' : 'server-status-offline'}"></i>
                                ${server.name}
                            </h5>
                            <button class="btn btn-sm btn-danger" onclick="deleteServer(${server.id})" title="Удалить сервер">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                        <p class="card-text">
                            <small class="text-muted">
                                Последний контакт: ${server.last_seen ? new Date(server.last_seen).toLocaleString() : 'Никогда'}
                            </small>
                        </p>
                        <span class="badge ${isOnline ? 'bg-success' : 'bg-danger'}">
                            ${isOnline ? 'Online' : 'Offline'}
                        </span>
                    </div>
                </div>
            </div>
        `;
        serversList.innerHTML += serverCard;
    });
}

async function loadAlerts() {
    const response = await fetch('/api/alerts?status=active&limit=5');
    const data = await response.json();
    
    const alertsContainer = document.getElementById('active-alerts');
    const alertCount = document.getElementById('alert-count');
    if (alertCount) alertCount.textContent = data.alerts.length;
    
    if (data.alerts.length === 0) {
        alertsContainer.innerHTML = '<p class="text-muted">Нет активных оповещений</p>';
        return;
    }
    
    alertsContainer.innerHTML = '';
    data.alerts.forEach(alert => {
        const alertElement = `
            <div class="alert ${alert.severity === 'critical' ? 'alert-critical alert-danger' : 'alert-warning alert-warning'} mb-2">
                <div class="d-flex justify-content-between">
                    <div>
                        <strong>${alert.metric_type}</strong> - ${alert.message}
                    </div>
                    <div>
                        <small class="text-muted">${new Date(alert.created_at).toLocaleString()}</small>
                        <button class="btn btn-sm btn-outline-primary ms-2" onclick="resolveAlert(${alert.id})">
                            Исправлено
                        </button>
                    </div>
                </div>
            </div>
        `;
        alertsContainer.innerHTML += alertElement;
    });
}

async function resolveAlert(alertId) {
    try {
        const response = await fetch(`/api/alerts/${alertId}/resolve`, {
            method: 'POST'
        });
        
        if (response.ok) {
            loadAlerts(); // Перезагружаем оповещения
        }
    } catch (error) {
        console.error('Error resolving alert:', error);
    }
}

async function deleteServer(serverId) {
    if (!confirm('Вы уверены, что хотите удалить этот сервер и все его оповещения? Это действие необратимо.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/servers/${serverId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showSuccess('Сервер удалён');
            loadDashboardData(); // Перезагружаем список
        } else {
            const error = await response.json();
            showError(error.error || 'Ошибка удаления сервера');
        }
    } catch (error) {
        console.error('Error deleting server:', error);
        showError('Ошибка удаления сервера');
    }
}

function refreshData() {
    loadDashboardData();
}

function showSuccess(message) {
    alert(message);
}

function showError(message) {
    alert('Ошибка: ' + message);
}