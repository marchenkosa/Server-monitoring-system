// Загрузка при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    loadAlerts();
    // Обновляем каждые 30 секунд
    setInterval(loadAlerts, 30000);
});

async function loadAlerts() {
    try {
        const statusFilter = document.getElementById('statusFilter').value;
        const severityFilter = document.getElementById('severityFilter').value;
        
        let url = '/api/alerts';
        const params = [];
        
        if (statusFilter !== 'all') {
            params.push(`status=${statusFilter}`);
        }
        
        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        // Фильтруем по уровню серьезности если нужно
        let filteredAlerts = data.alerts;
        if (severityFilter !== 'all') {
            filteredAlerts = data.alerts.filter(alert => alert.severity === severityFilter);
        }
        
        displayAlerts(filteredAlerts);
        updateStats(filteredAlerts);
        
    } catch (error) {
        console.error('Error loading alerts:', error);
        showError('Ошибка загрузки оповещений');
    }
}

function displayAlerts(alerts) {
    const table = document.getElementById('alertsTable');
    
    if (alerts.length === 0) {
        table.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Нет оповещений</td></tr>';
        return;
    }
    
    // Сортируем по времени (новые сверху)
    alerts.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    table.innerHTML = '';
    alerts.forEach(alert => {
        const row = document.createElement('tr');
        const severityClass = getSeverityClass(alert.severity);
        const statusClass = alert.status === 'active' ? 'warning' : 'success';
        
        row.innerHTML = `
            <td>${formatDateTime(alert.created_at)}</td>
            <td>${alert.server ? alert.server.name : `Server ${alert.server_id}`}</td>
            <td>${alert.metric_type}</td>
            <td>${alert.message}</td>
            <td><span class="badge bg-${severityClass}">${getSeverityText(alert.severity)}</span></td>
            <td><span class="badge bg-${statusClass}">${getStatusText(alert.status)}</span></td>
            <td>
                ${alert.status === 'active' ? 
                    `<button class="btn btn-sm btn-success" onclick="resolveAlert(${alert.id})" title="Отметить как исправленное">
                        <i class="fas fa-check"></i>
                    </button>` : 
                    `<span class="text-muted">Решено</span>`
                }
            </td>
        `;
        table.appendChild(row);
    });
}

function updateStats(alerts) {
    const criticalCount = alerts.filter(a => a.severity === 'critical' && a.status === 'active').length;
    const warningCount = alerts.filter(a => a.severity === 'warning' && a.status === 'active').length;
    const activeCount = alerts.filter(a => a.status === 'active').length;
    
    document.getElementById('criticalCount').textContent = criticalCount;
    document.getElementById('warningCount').textContent = warningCount;
    document.getElementById('activeCount').textContent = activeCount;
}

function getSeverityClass(severity) {
    switch(severity) {
        case 'critical': return 'danger';
        case 'warning': return 'warning';
        case 'info': return 'info';
        default: return 'secondary';
    }
}

function getSeverityText(severity) {
    switch(severity) {
        case 'critical': return 'Критический';
        case 'warning': return 'Предупреждение';
        case 'info': return 'Информация';
        default: return severity;
    }
}

function getStatusText(status) {
    switch(status) {
        case 'active': return 'Активно';
        case 'resolved': return 'Решено';
        case 'acknowledged': return 'Подтверждено';
        default: return status;
    }
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU');
}

async function resolveAlert(alertId) {
    try {
        const response = await fetch(`/api/alerts/${alertId}/resolve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            showSuccess('Оповещение отмечено как решенное');
            loadAlerts(); // Перезагружаем список
        } else {
            throw new Error('Failed to resolve alert');
        }
    } catch (error) {
        console.error('Error resolving alert:', error);
        showError('Ошибка при отметке оповещения');
    }
}

function refreshAlerts() {
    loadAlerts();
    showInfo('Оповещения обновлены');
}

// Уведомления
function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'danger');
}

function showInfo(message) {
    showNotification(message, 'info');
}

function showNotification(message, type) {
    // Простая реализация уведомлений
    alert(message); // Можно заменить на toast-уведомления
}