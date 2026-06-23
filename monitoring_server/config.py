import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'monitoring-system-secret-key-2024'
    
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'database', 'monitoring.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    INFLUXDB_HOST = 'localhost'
    INFLUXDB_PORT = 8086
    INFLUXDB_DATABASE = 'monitoring_metrics'
    
    SERVER_HOST = '10.10.10.222'
    SERVER_PORT = 5000
    
    ALERT_CHECK_INTERVAL = 60
    ALERT_COOLDOWN = 300
    
    ALERT_THRESHOLDS = {
        'cpu_percent': 90,
        'memory_percent': 85,
        'disk_percent': 90,
        'service_stopped': True
    }

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}