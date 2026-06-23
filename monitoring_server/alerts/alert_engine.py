import logging
from datetime import datetime, timedelta
from models.database import db, AlertRule, Alert, Server

class AlertEngine:
    def __init__(self):
        self.rules_initialized = False
        self.sent_alerts = {}

    def ensure_rules_initialized(self):
        if not self.rules_initialized:
            self.setup_default_rules()
            self.rules_initialized = True

    def setup_default_rules(self):
        try:
            if AlertRule.query.count() == 0:
                default_rules = [
                    AlertRule(
                        name="High CPU Usage",
                        metric_type="cpu_percent",
                        condition="gt",
                        threshold=90.0,
                        message_template="CPU usage is {value}% (threshold: {threshold}%)",
                        cooldown_minutes=5
                    ),
                    AlertRule(
                        name="High Memory Usage",
                        metric_type="memory_percent",
                        condition="gt",
                        threshold=85.0,
                        message_template="Memory usage is {value}% (threshold: {threshold}%)",
                        cooldown_minutes=5
                    ),
                    AlertRule(
                        name="Low Disk Space",
                        metric_type="disk_percent",
                        condition="gt",
                        threshold=90.0,
                        message_template="Disk {drive} usage is {value}% (threshold: {threshold}%)",
                        cooldown_minutes=30
                    ),
                    AlertRule(
                        name="Service Stopped",
                        metric_type="service_status",
                        condition="eq",
                        threshold=0,
                        message_template="Service {service_name} is stopped",
                        cooldown_minutes=1
                    )
                ]
                db.session.bulk_save_objects(default_rules)
                db.session.commit()
                logging.info("Default alert rules created")
        except Exception as e:
            logging.error(f"Error setting up default rules: {e}")

    def should_send_alert(self, server_id, rule_id, cooldown_minutes):
        """Проверка кулдауна для конкретного правила и сервера"""
        key = f"{server_id}_{rule_id}"
        last_sent = self.sent_alerts.get(key)
        if not last_sent:
            return True
        return datetime.utcnow() - last_sent > timedelta(minutes=cooldown_minutes)

    def mark_alert_sent(self, server_id, rule_id):
        """Отметка времени отправки оповещения"""
        key = f"{server_id}_{rule_id}"
        self.sent_alerts[key] = datetime.utcnow()

    def _create_alert(self, server_id, metric_type, message, severity='warning'):
        """Создание записи оповещения в БД"""
        try:
            alert = Alert(
                server_id=server_id,
                metric_type=metric_type,
                message=message,
                severity=severity
            )
            db.session.add(alert)
            db.session.commit()
            logging.info(f"Alert created for server {server_id}: {metric_type} - {message}")
        except Exception as e:
            logging.error(f"Error creating alert: {e}")

    def check_metrics(self, metrics_data):
        try:
            self.ensure_rules_initialized()
            server_name = metrics_data['agent_name']
            server = db.session.query(Server).filter_by(name=server_name).first()
            if not server:
                logging.warning(f"Server {server_name} not found in DB")
                return
            server_id = server.id

            self._check_cpu(server_id, metrics_data['cpu_percent'])
            memory_percent = metrics_data['memory_usage']['percent']
            self._check_memory(server_id, memory_percent)
            self._check_disks(server_id, metrics_data['disk_usage'])
            self._check_services(server_id, metrics_data['services_status'])

        except Exception as e:
            logging.error(f"Error in alert engine: {e}")

    def _check_cpu(self, server_id, cpu_percent):
        rule = AlertRule.query.filter_by(metric_type="cpu_percent", is_active=True).first()
        if rule and cpu_percent > rule.threshold:
            if self.should_send_alert(server_id, rule.id, rule.cooldown_minutes):
                message = rule.message_template.format(value=cpu_percent, threshold=rule.threshold)
                self._create_alert(server_id, "CPU", message, "warning")
                self.mark_alert_sent(server_id, rule.id)
            else:
                logging.debug(f"CPU alert suppressed by cooldown for server {server_id}")

    def _check_memory(self, server_id, memory_percent):
        rule = AlertRule.query.filter_by(metric_type="memory_percent", is_active=True).first()
        if rule and memory_percent > rule.threshold:
            if self.should_send_alert(server_id, rule.id, rule.cooldown_minutes):
                message = rule.message_template.format(value=memory_percent, threshold=rule.threshold)
                self._create_alert(server_id, "Memory", message, "warning")
                self.mark_alert_sent(server_id, rule.id)

    def _check_disks(self, server_id, disk_usage):
        rule = AlertRule.query.filter_by(metric_type="disk_percent", is_active=True).first()
        if rule:
            for drive, usage in disk_usage.items():
                if 'error' not in usage and usage['percent'] > rule.threshold:
                    if self.should_send_alert(server_id, rule.id, rule.cooldown_minutes):
                        message = rule.message_template.format(
                            drive=drive,
                            value=usage['percent'],
                            threshold=rule.threshold
                        )
                        self._create_alert(server_id, f"Disk {drive}", message, "critical")
                        self.mark_alert_sent(server_id, rule.id)
                    else:
                        logging.debug(f"Disk alert for {drive} suppressed by cooldown")

    def _check_services(self, server_id, services_status):
        rule = AlertRule.query.filter_by(metric_type="service_status", is_active=True).first()
        if rule:
            for service_name, status in services_status.items():
                if status.get('status') == 'stopped':
                    if self.should_send_alert(server_id, rule.id, rule.cooldown_minutes):
                        message = rule.message_template.format(service_name=service_name)
                        self._create_alert(server_id, f"Service {service_name}", message, "critical")
                        self.mark_alert_sent(server_id, rule.id)
                    else:
                        logging.debug(f"Service alert for {service_name} suppressed by cooldown")