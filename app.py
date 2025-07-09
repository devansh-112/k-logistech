import os
import logging
from flask import Flask
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
from database import db
from flask_mail import Mail

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Import branding config
try:
    from branding_config import SITE_NAME, COMPANY_NAME
except ImportError:
    SITE_NAME = "GotoFast Logistics"
    COMPANY_NAME = "GotoFast Logistics Pvt Ltd"

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "logistics-secret-key-2024")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config['SITE_NAME'] = SITE_NAME
app.config['COMPANY_NAME'] = COMPANY_NAME

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///logistics.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Configure upload folder
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploaded_gst_bills')
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Configure Flask-Mail (fill in your SMTP details)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'gotofasttransport@gmail.com'
app.config['MAIL_PASSWORD'] = 'Deva@1234'
app.config['MAIL_DEFAULT_SENDER'] = 'gotofasttransport@gmail.com'
mail = Mail(app)

# Initialize the app with the extension
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

@login_manager.user_loader
def load_user(user_id):
    from models import Admin, DeliveryPartner
    if user_id.startswith('admin_'):
        admin_id = int(user_id.split('_')[1])
        return Admin.query.get(admin_id)
    elif user_id.startswith('partner_'):
        partner_id = int(user_id.split('_')[1])
        return DeliveryPartner.query.get(partner_id)
    return None

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()
    logging.info("Database tables created successfully")
    
    # Initialize default content
    from init_data import initialize_contact_settings
    initialize_contact_settings()

# Import routes after app is created
from routes import *

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
