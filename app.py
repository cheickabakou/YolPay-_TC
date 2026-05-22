from flask import Flask
from models.database import init_db
from routes.public import public_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.admin import admin_bp
from routes.driver import driver_bp
from routes.passenger import passenger_bp
from routes.urban import urban_bp
from routes.api import api_bp

app = Flask(__name__)
app.secret_key = 'yolpayi_secret_key_2024_gumushane'

app.register_blueprint(public_bp)
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(driver_bp, url_prefix='/driver')
app.register_blueprint(passenger_bp, url_prefix='/passenger')
app.register_blueprint(urban_bp, url_prefix='/urban')
app.register_blueprint(api_bp, url_prefix='/api')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
