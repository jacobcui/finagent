from flask import Flask
from src.framework.config import Config
from src.framework.extensions import db, login_manager, migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    from src.framework.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    from src.framework.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from src.framework.views import main_bp
    app.register_blueprint(main_bp)

    return app
