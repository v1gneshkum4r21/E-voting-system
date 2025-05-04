from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Import blueprints (to be created later)
from app.controllers.auth_controller import auth_bp
from app.controllers.voter_controller import voter_bp
from app.controllers.candidate_controller import candidate_bp
from app.controllers.admin_controller import admin_bp
from app.controllers.index_controller import index_bp
from app.models.user import User
from app.utils.database import init_db, db_path

def create_app():
    app = Flask(__name__, 
                template_folder='app/templates',
                static_folder='app/static')
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['UPLOAD_FOLDER'] = os.path.join('app', 'static', 'uploads')
    
    # Add now() function to Jinja environment
    app.jinja_env.globals['now'] = datetime.now
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize database
    init_db()
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import get_user_by_id
        return get_user_by_id(int(user_id))
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(voter_bp)
    app.register_blueprint(candidate_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(index_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500
    
    # Home route
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True) 