from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging
import atexit
import os

from config import config
from models.database import db, User
from models.influx_manager import InfluxDBManager
from alerts.alert_engine import AlertEngine
from api.endpoints import register_endpoints
from forms import LoginForm, RegistrationForm

influx_manager = None
alert_engine = None

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        logging.info(f"Created database directory: {db_dir}")
    
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    with app.app_context():
        init_managers(app)
        register_endpoints(app, influx_manager, alert_engine)
    
    @app.route('/')
    @login_required
    def dashboard():
        return render_template('dashboard.html')
    
    @app.route('/alerts')
    @login_required
    def alerts_page():
        return render_template('alerts.html')
    
    @app.route('/servers')
    @login_required
    def servers_page():
        return render_template('servers.html')
    
    @app.route('/admin')
    @login_required
    def admin_page():
        if not current_user.is_admin:
            flash('Доступ запрещён. Требуются права администратора.', 'danger')
            return redirect(url_for('dashboard'))
        form = RegistrationForm()
        return render_template('admin.html', registration_form=form)
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user is None or not user.check_password(form.password.data):
                flash('Неверное имя пользователя или пароль', 'danger')
                return redirect(url_for('login'))
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard')
            return redirect(next_page)
        return render_template('login.html', form=form)
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Вы вышли из системы.', 'info')
        return redirect(url_for('login'))
    
    @app.route('/register', methods=['GET', 'POST'])
    @login_required
    def register():
        if not current_user.is_admin:
            flash('Доступ запрещён. Требуются права администратора.', 'danger')
            return redirect(url_for('dashboard'))
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(username=form.username.data, is_admin=form.is_admin.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash(f'Пользователь {form.username.data} успешно создан.', 'success')
            return redirect(url_for('admin_page'))
        return render_template('register.html', form=form)
    
    @app.route('/api/users', methods=['GET'])
    @login_required
    def get_users():
        if not current_user.is_admin:
            return jsonify({'error': 'Forbidden'}), 403
        users = User.query.all()
        return jsonify([{
            'id': u.id,
            'username': u.username,
            'is_admin': u.is_admin,
            'created_at': u.created_at.isoformat() + 'Z'
        } for u in users])
    
    @app.route('/api/users/<int:user_id>', methods=['DELETE'])
    @login_required
    def delete_user(user_id):
        if not current_user.is_admin:
            return jsonify({'error': 'Forbidden'}), 403
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            return jsonify({'error': 'Нельзя удалить свою учётную запись'}), 400
        db.session.delete(user)
        db.session.commit()
        return jsonify({'status': 'success'})
    
    def cleanup_old_alerts():
        with app.app_context():
            try:
                from models.database import Alert
                cutoff_date = datetime.utcnow() - timedelta(days=7)
                old_alerts = Alert.query.filter(
                    Alert.created_at < cutoff_date,
                    Alert.status == 'resolved'
                )
                count = old_alerts.count()
                old_alerts.delete()
                db.session.commit()
                logging.info(f"Cleaned up {count} old alerts")
            except Exception as e:
                logging.error(f"Error cleaning alerts: {e}")
    
    def cleanup_old_metrics():
        with app.app_context():
            try:
                from models.database import ServerMetric
                cutoff_date = datetime.utcnow() - timedelta(days=3)
                old_metrics = ServerMetric.query.filter(ServerMetric.timestamp < cutoff_date)
                count = old_metrics.count()
                old_metrics.delete()
                db.session.commit()
                logging.info(f"Cleaned up {count} old metrics")
            except Exception as e:
                logging.error(f"Error cleaning metrics: {e}")
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_old_alerts, 'interval', hours=6)
    scheduler.add_job(cleanup_old_metrics, 'interval', hours=12)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    
    return app

def init_managers(app):
    global influx_manager, alert_engine
    try:
        influx_manager = InfluxDBManager(
            app.config['INFLUXDB_HOST'],
            app.config['INFLUXDB_PORT'],
            app.config['INFLUXDB_DATABASE']
        )
        logging.info("InfluxDB manager initialized")
    except Exception as e:
        logging.warning(f"InfluxDB unavailable: {e}")
        influx_manager = None
    alert_engine = AlertEngine()

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('monitoring_server.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    app = create_app()
    
    with app.app_context():
        db.create_all()
        try:
            import sqlite3
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            if db_uri.startswith('sqlite:///'):
                db_path = db_uri.replace('sqlite:///', '')
                if not os.path.isabs(db_path):
                    db_path = os.path.join(os.path.dirname(__file__), db_path)
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA table_info(servers)")
                    columns = [col[1] for col in cursor.fetchall()]
                    if 'system_info' not in columns:
                        cursor.execute("ALTER TABLE servers ADD COLUMN system_info TEXT")
                        conn.commit()
                        logging.info("Added column system_info to servers table")
                    conn.close()
        except Exception as e:
            logging.error(f"Migration error: {e}")
        
        if User.query.count() == 0:
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            logging.info("Default admin user created (username: admin, password: admin123)")
        
        logging.info("Database tables created/checked")
    
    host = app.config['SERVER_HOST']
    port = app.config['SERVER_PORT']
    print("=" * 50)
    print("Monitoring Server Starting")
    print("=" * 50)
    print(f"Server: {host}:{port}")
    print(f"Dashboard: http://{host}:{port}")
    print(f"API Health: http://{host}:{port}/api/health")
    print("Default admin: admin / admin123")
    print("=" * 50)
    
    app.run(host=host, port=port, debug=True)