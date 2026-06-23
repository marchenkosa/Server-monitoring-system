from influxdb import InfluxDBClient
import logging

class InfluxDBManager:
    def __init__(self, host='localhost', port=8086, database='monitoring_metrics'):
        self.host = host
        self.port = port
        self.database = database
        self.client = None
        self.setup_database()
        
    def setup_database(self):
        """Создание базы данных если не существует"""
        try:
            self.client = InfluxDBClient(
                host=self.host, 
                port=self.port, 
                timeout=10,
                retries=3
            )
            
            # Проверяем соединение
            self.client.ping()
            
            # Создаем базу данных если не существует
            databases = self.client.get_list_database()
            if not any(db['name'] == self.database for db in databases):
                self.client.create_database(self.database)
                logging.info(f"Создана база данных InfluxDB: {self.database}")
            
            self.client.switch_database(self.database)
            logging.info(f"InfluxDB подключен: {self.host}:{self.port}/{self.database}")
            
        except Exception as e:
            logging.warning(f"InfluxDB недоступен на {self.host}:{self.port}: {e}")
            self.client = None
    
    def is_available(self):
        """Проверка доступности InfluxDB"""
        return self.client is not None
    
    def write_metrics(self, metrics_data):
        """Запись метрик в InfluxDB"""
        if not self.is_available():
            logging.debug("InfluxDB недоступен, пропускаем запись метрик")
            return False
            
        try:
            points = []
            timestamp_ns = int(metrics_data['timestamp'] * 1e9)  # Конвертируем в наносекунды
            
            # CPU метрики
            points.append({
                "measurement": "cpu",
                "tags": {
                    "server": metrics_data['agent_name']
                },
                "time": timestamp_ns,
                "fields": {
                    "usage_percent": float(metrics_data['cpu_percent'])
                }
            })
            
            # Memory метрики
            memory = metrics_data['memory_usage']
            points.append({
                "measurement": "memory",
                "tags": {
                    "server": metrics_data['agent_name']
                },
                "time": timestamp_ns,
                "fields": {
                    "total_gb": memory['total_gb'],
                    "used_gb": memory['used_gb'],
                    "available_gb": memory['available_gb'],
                    "usage_percent": memory['percent']
                }
            })
            
            # Disk метрики
            for drive, usage in metrics_data['disk_usage'].items():
                if 'error' not in usage:
                    points.append({
                        "measurement": "disk",
                        "tags": {
                            "server": metrics_data['agent_name'],
                            "drive": drive
                        },
                        "time": timestamp_ns,
                        "fields": {
                            "total_gb": usage['total_gb'],
                            "used_gb": usage['used_gb'],
                            "free_gb": usage['free_gb'],
                            "usage_percent": usage['percent']
                        }
                    })
            
            # Network метрики
            network = metrics_data['network_io']
            points.append({
                "measurement": "network",
                "tags": {
                    "server": metrics_data['agent_name']
                },
                "time": timestamp_ns,
                "fields": {
                    "bytes_sent": network['bytes_sent'],
                    "bytes_recv": network['bytes_recv'],
                    "packets_sent": network.get('packets_sent', 0),
                    "packets_recv": network.get('packets_recv', 0)
                }
            })
            
            # Service статусы
            for service_name, status in metrics_data['services_status'].items():
                points.append({
                    "measurement": "services",
                    "tags": {
                        "server": metrics_data['agent_name'],
                        "service": service_name
                    },
                    "time": timestamp_ns,
                    "fields": {
                        "status": 1 if status.get('status') == 'running' else 0,
                        "status_text": status.get('status', 'unknown')
                    }
                })
            
            success = self.client.write_points(points)
            if success:
                logging.debug(f"Метрики записаны в InfluxDB для {metrics_data['agent_name']}")
            return success
            
        except Exception as e:
            logging.error(f"Ошибка записи в InfluxDB: {e}")
            return False
    
    def query_metrics(self, measurement, server, time_range='1h'):
        """Запрос метрик из InfluxDB"""
        if not self.is_available():
            logging.debug("InfluxDB недоступен, возвращаем пустой список")
            return []
            
        try:
            query = f'''
            SELECT * FROM "{measurement}"
            WHERE "server" = '{server}'
            AND time > now() - {time_range}
            ORDER BY time DESC
            '''
            result = self.client.query(query)
            return list(result.get_points())
        except Exception as e:
            logging.error(f"Ошибка запроса к InfluxDB: {e}")
            return []