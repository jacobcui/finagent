from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from src.framework.models import User
from src.framework.extensions import db
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

auth_bp = Blueprint('auth', __name__)

def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-confirm-salt')

def confirm_verification_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='email-confirm-salt', max_age=expiration)
    except:
        return False
    return email

# --- API Routes ---

@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400

    new_user = User(email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    # Simulate Email Sending
    token = generate_verification_token(email)
    verify_url = url_for('auth.verify_email', token=token, _external=True)

    # Return verification link in response for testing convenience
    return jsonify({
        'message': 'Registration successful.',
        'mock_verify_link': verify_url
    }), 201

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Check Trial
    if not user.is_trial_active:
        return jsonify({'error': 'Trial expired'}), 403

    # Check Verification (Optional, based on requirements, but good practice)
    if not user.is_verified:
        return jsonify({'error': 'Email not verified', 'is_verified': False}), 403

    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'is_verified': user.is_verified,
            'trial_end_date': user.trial_end_date.isoformat() if user.trial_end_date else None
        }
    }), 200

# --- Web Routes ---

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered.')
            return redirect(url_for('auth.register'))

        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Simulate Email Sending
        token = generate_verification_token(email)
        verify_url = url_for('auth.verify_email', token=token, _external=True)
        print(f"\n[MOCK EMAIL] To: {email}")
        print(f"[MOCK EMAIL] Subject: Verify your account")
        print(f"[MOCK EMAIL] Link: {verify_url}\n")

        flash('Registration successful! Please check your console for the verification link.')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Please check your login details and try again.')
            return redirect(url_for('auth.login'))

        login_user(user)

        # Trial Check
        if not user.is_trial_active:
            flash('Your 3-month trial has expired. Please renew your subscription.', 'warning')

        return redirect(url_for('main.dashboard'))

    return render_template('login.html')

@auth_bp.route('/verify/<token>')
def verify_email(token):
    email = confirm_verification_token(token)
    if not email:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first_or_404()
    if user.is_verified:
        flash('Account already verified. Please login.', 'success')
    else:
        user.is_verified = True
        db.session.commit()
        flash('You have verified your account. Thanks!', 'success')

    return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
