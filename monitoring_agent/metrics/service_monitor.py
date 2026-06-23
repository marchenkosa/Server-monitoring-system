import psutil
import win32service
import win32serviceutil

class ServiceMonitor:
    def __init__(self, services_to_monitor):
        self.services = services_to_monitor
    
    def get_services_status(self):
        """Статус Windows служб"""
        services_status = {}
        
        for service_name in self.services:
            try:
                status = self.check_service_status(service_name)
                services_status[service_name] = status
            except Exception as e:
                services_status[service_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return services_status
    
    def check_service_status(self, service_name):
        """Проверка статуса конкретной службы"""
        try:
            # Попробовать через win32service
            scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
            try:
                service = win32service.OpenService(scm, service_name, win32service.SERVICE_QUERY_STATUS)
                status = win32service.QueryServiceStatus(service)
                
                status_map = {
                    win32service.SERVICE_STOPPED: 'stopped',
                    win32service.SERVICE_START_PENDING: 'start_pending',
                    win32service.SERVICE_STOP_PENDING: 'stop_pending',
                    win32service.SERVICE_RUNNING: 'running',
                    win32service.SERVICE_CONTINUE_PENDING: 'continue_pending',
                    win32service.SERVICE_PAUSE_PENDING: 'pause_pending',
                    win32service.SERVICE_PAUSED: 'paused'
                }
                
                return {
                    'status': status_map.get(status[1], 'unknown'),
                    'win32_code': status[1]
                }
                
            finally:
                win32service.CloseServiceHandle(service)
                win32service.CloseServiceHandle(scm)
                
        except Exception:
            # Fallback: проверка через имя процесса
            return self.check_process_status(service_name)
    
    def check_process_status(self, process_name):
        """Проверка через имя процесса (fallback)"""
        for proc in psutil.process_iter(['name']):
            if process_name.lower() in proc.info['name'].lower():
                return {'status': 'running', 'method': 'process_check'}
        
        return {'status': 'stopped', 'method': 'process_check'}