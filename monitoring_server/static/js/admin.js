async function loadUsers() {
    try {
        const response = await fetch('/api/users');
        const users = await response.json();
        
        const table = document.getElementById('usersTable');
        table.innerHTML = '';
        
        users.forEach(user => {
            const row = table.insertRow();
            row.insertCell(0).textContent = user.id;
            row.insertCell(1).textContent = user.username;
            row.insertCell(2).textContent = user.is_admin ? 'Да' : 'Нет';
            row.insertCell(3).textContent = new Date(user.created_at).toLocaleString('ru-RU');
            const actionsCell = row.insertCell(4);
            if (!user.is_admin || user.username !== 'admin') { // не даём удалить встроенного admin
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn btn-sm btn-danger';
                deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
                deleteBtn.onclick = () => deleteUser(user.id, user.username);
                actionsCell.appendChild(deleteBtn);
            } else {
                actionsCell.textContent = '—';
            }
        });
    } catch (error) {
        console.error('Error loading users:', error);
        alert('Ошибка загрузки списка пользователей');
    }
}

async function deleteUser(userId, username) {
    if (!confirm(`Удалить пользователя "${username}"? Это действие необратимо.`)) {
        return;
    }
    try {
        const response = await fetch(`/api/users/${userId}`, {
            method: 'DELETE'
        });
        if (response.ok) {
            alert('Пользователь удалён');
            loadUsers();
        } else {
            const error = await response.json();
            alert('Ошибка: ' + (error.error || 'Не удалось удалить пользователя'));
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        alert('Ошибка при удалении пользователя');
    }
}

function confirmRestart() {
    const modal = new bootstrap.Modal(document.getElementById('restartConfirmModal'));
    modal.show();
    document.getElementById('confirmRestartBtn').onclick = async function() {
        try {
            const response = await fetch('/api/admin/restart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            if (response.ok) {
                alert('Перезапуск сервера инициирован. Вы будете выведены из системы.');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
            } else {
                alert('Ошибка: ' + data.error);
            }
        } catch (error) {
            console.error('Error restarting server:', error);
            alert('Ошибка при перезапуске сервера. Проверьте логи.');
        }
        modal.hide();
    };
}

document.addEventListener('DOMContentLoaded', loadUsers);