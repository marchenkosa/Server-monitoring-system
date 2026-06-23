import os
import time
import json
import logging
import schedule
import requests
import yaml
from metrics.system_metrics import SystemMetrics
from metrics.service_monitor import ServiceMonitor

class MonitoringAgent:
    def __init__(self, config_path=None):
        # Если путь не передан, ищем config.yaml в папке скрипта
        if config_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, 'config.yaml')
        self.load_config(config_path)
        self.system_metrics = SystemMetrics()
        self.service_monitor = ServiceMonitor(self.config['monitoring']['services'])
        self.setup_logging()
        
    def load_config(self, config_path):
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('agent.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def collect_metrics(self):
        """Сбор всех метрик"""
        try:
            metrics = {
                'agent_name': self.config['agent']['name'],
                'timestamp': time.time(),
                'cpu_percent': self.system_metrics.get_cpu_usage(),
                'memory_usage': self.system_metrics.get_memory_usage(),
                'disk_usage': self.system_metrics.get_disk_usage(
                    self.config['monitoring']['disks']
                ),
                'network_io': self.system_metrics.get_network_io(),
                'services_status': self.service_monitor.get_services_status(),
                'system_uptime': self.system_metrics.get_system_uptime()
            }
            return metrics
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return None
    
    def send_metrics(self, metrics):
        """Отправка метрик на сервер"""
        if not metrics:
            return False
            
        try:
            response = requests.post(
                f"{self.config['server']['url']}{self.config['server']['endpoint']}",
                json=metrics,
                timeout=self.config['server']['timeout']
            )
            
            if response.status_code == 200:
                self.logger.info("Metrics sent successfully")
                return True
            else:
                self.logger.error(f"Server returned status code: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send metrics: {e}")
            return False
    
    def run(self):
        """Основной цикл работы агента"""
        self.logger.info("Starting monitoring agent...")
        
        def job():
            self.logger.info("Collecting metrics...")
            metrics = self.collect_metrics()
            if metrics:
                success = self.send_metrics(metrics)
                if not success:
                    self.logger.warning("Failed to send metrics, will retry next cycle")
        
        # Запуск по расписанию
        schedule.every(self.config['agent']['interval']).seconds.do(job)
        
        # Первый запуск сразу
        job()
        
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    agent = MonitoringAgent()
    agent.run()