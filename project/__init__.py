from flask import Flask
from config import Config
from .extensions import db, login_manager, bcrypt
from .models import User, PredictionLog
import os

def create_app(config_class=Config):
    """
    Application factory pattern.
    Initializes and configures the Flask application.
    """
    app = Flask(__name__, instance_relative_config=True)
    
    # Load configuration from config.py
    app.config.from_object(config_class)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Configure Flask-Login
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'
    login_manager.login_message = "Please log in to access this page."

    @login_manager.user_loader
    def load_user(user_id):
        # User loader callback for Flask-Login
        return User.query.get(int(user_id))

    # Register Blueprints (routes)
    #
    # !!! IMPORTANT !!!
    # This import is *inside* the function to prevent circular imports.
    # If you have it at the top of the file, your app will break.
    #
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Create database tables
    with app.app_context():
        db.create_all()
        
        # --- Create Admin User (Optional) ---
        if not User.query.filter_by(email='admin@app.com').first():
            print("Creating default admin user...")
            admin_user = User(
                username='admin',
                email='admin@app.com',
                is_admin=True
            )
            admin_user.set_password('admin123') # Change this in production
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created.")

    return app