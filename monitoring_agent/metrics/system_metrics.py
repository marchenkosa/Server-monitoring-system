import psutil
import pythoncom
import wmi
from datetime import datetime

class SystemMetrics:
    def __init__(self):
        pythoncom.CoInitialize()  # Важно для WMI в потоках
        self.wmi_conn = wmi.WMI()
        
    def get_cpu_usage(self):
        """Загрузка CPU в процентах"""
        return psutil.cpu_percent(interval=1)
    
    def get_memory_usage(self):
        """Использование памяти"""
        memory = psutil.virtual_memory()
        return {
            'total_gb': round(memory.total / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'percent': memory.percent
        }
    
    def get_disk_usage(self, drives):
        """Использование дискового пространства"""
        disk_usage = {}
        for drive in drives:
            try:
                usage = psutil.disk_usage(drive)
                disk_usage[drive] = {
                    'total_gb': round(usage.total / (1024**3), 2),
                    'used_gb': round(usage.used / (1024**3), 2),
                    'free_gb': round(usage.free / (1024**3), 2),
                    'percent': usage.percent
                }
            except Exception as e:
                disk_usage[drive] = {'error': str(e)}
        return disk_usage
    
    def get_network_io(self):
        """Сетевая активность"""
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv
        }
    
    def get_system_uptime(self):
        """Время работы системы"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        return {
            'boot_time': boot_time.isoformat(),
            'uptime_seconds': int(uptime.total_seconds()),
            'uptime_days': uptime.days
        }
    
    def get_disk_io(self):
        """Дисковая I/O активность"""
        disk_io = psutil.disk_io_counters()
        return {
            'read_count': disk_io.read_count,
            'write_count': disk_io.write_count,
            'read_bytes': disk_io.read_bytes,
            'write_bytes': disk_io.write_bytes
        }