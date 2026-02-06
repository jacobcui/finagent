from src.framework.app import create_app
from src.framework.extensions import db

app = create_app()

def init_db():
    with app.app_context():
        # In a real scenario, use Flask-Migrate (alembic)
        # For 'out-of-the-box' runnability, we create all tables here
        db.create_all()
        print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
