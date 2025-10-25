from flask import (
    render_template, redirect, url_for,
    flash, request, jsonify, Blueprint, current_app
)
from flask_login import login_user, current_user, logout_user, login_required
from .forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm # Ensure these are correct
from .models import User, PredictionLog
from .extensions import db, bcrypt, mail # Ensure mail is imported if used
from .ml_logic import train_and_predict, STOCK_TICKERS
from flask_mail import Message # Ensure this is imported if mail is used
import json
from functools import wraps
from datetime import datetime

main = Blueprint('main', __name__)

# --- (admin_required decorator and email sending function if used) ---
def admin_required(f):
     @wraps(f)
     def decorated_function(*args, **kwargs):
         if not current_user.is_authenticated or not current_user.is_admin:
             flash("You do not have permission to access this page.", "danger")
             return redirect(url_for('main.home'))
         return f(*args, **kwargs)
     return decorated_function

# --- (Email sending function send_reset_email if used) ---
# Define send_reset_email function here if you are using password reset

# --- Routes ---

@main.route("/")
@main.route("/home")
@login_required
def home():
    """Renders the main dashboard page."""
    stock_options = list(STOCK_TICKERS.keys())
    # --- KNN removed from model_options ---
    model_options = ['Linear Regression', 'Random Forest', 'XGBoost'] # <-- REMOVED 'KNN'
    # --- End of change ---

    return render_template(
        'home.html',
        title='Prediction Dashboard',
        stocks=stock_options,
        models=model_options
    )

@main.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)


@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))

# --- (Password reset routes: forgot_password, reset_token if added) ---
# Add forgot_password and reset_token routes here if you are using them

@main.route("/admin")
@login_required
@admin_required
def admin():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.id.desc()).paginate(page=page, per_page=10)
    logs = PredictionLog.query.order_by(PredictionLog.timestamp.desc()).paginate(page=page, per_page=10)
    return render_template('admin.html', title='Admin Dashboard', users=users, logs=logs)

# --- API Route (for ML) - UPDATED ---
@main.route("/predict", methods=['POST'])
@login_required
def predict():
    """
    Handles AJAX request for single date prediction.
    """
    if not request.is_json:
        return jsonify({"error": "Invalid request: Must be JSON"}), 400

    data = request.get_json()

    stock_name = data.get('stock')
    model_name = data.get('model')
    prediction_date = data.get('prediction_date')

    if not all([stock_name, model_name, prediction_date]):
        return jsonify({"error": "Missing required fields (stock, model, prediction_date)"}), 400

    try:
        result = train_and_predict(
            stock_name,
            model_name,
            prediction_date
        )

        if 'error' in result:
            return jsonify(result), 400

        try:
            predicted_date_obj = datetime.strptime(result['predicted_date'], '%Y-%m-%d').date()

            log_entry = PredictionLog(
                user_id=current_user.id,
                stock_ticker=stock_name,
                model_used=model_name,
                predicted_date=predicted_date_obj,
                predicted_price=result['predicted_price'],
                confidence=result['confidence']
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as log_e:
             db.session.rollback()
             print(f"Error logging prediction: {log_e}")

        return jsonify(result)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Prediction route failed: {e}", exc_info=True)
        return jsonify({"error": f"An internal error occurred."}), 500