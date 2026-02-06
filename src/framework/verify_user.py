import sys

from src.framework.app import create_app
from src.framework.extensions import db
from src.framework.models import User


def verify_user(email):
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_verified = True
            db.session.commit()
            print(f"Successfully verified user: {email}")
        else:
            print(f"Error: User with email '{email}' not found.")
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m src.framework.verify_user <email>")
        sys.exit(1)

    email = sys.argv[1]
    verify_user(email)
