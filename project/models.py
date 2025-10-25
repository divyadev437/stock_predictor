# ... (User model remains the same) ...
from .extensions import db, bcrypt
from flask_login import UserMixin
from datetime import datetime, date # Add date

class User(UserMixin, db.Model):
    # ... (no changes needed here) ...
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    logs = db.relationship('PredictionLog', backref='user', lazy=True)

    # ... (methods set_password, check_password, get_reset_token, verify_reset_token) ...
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    # --- Methods for Password Reset (if you added them) ---
    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}, salt='password-reset-salt')

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='password-reset-salt', max_age=expires_sec)
            user_id = data.get('user_id')
        except Exception:
            return None
        return User.query.get(user_id)
    # --- End of Reset Methods ---

    def __repr__(self):
        return f'<User {self.username}>'


class PredictionLog(db.Model):
    """
    PredictionLog model storing single date predictions.
    """
    __tablename__ = 'prediction_log' # Keep table name consistent

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_ticker = db.Column(db.String(20), nullable=False)
    model_used = db.Column(db.String(50), nullable=False)
    # --- Updated Fields ---
    predicted_date = db.Column(db.Date, nullable=False) # Store the target date
    predicted_price = db.Column(db.Float, nullable=False) # Store the single predicted price
    confidence = db.Column(db.String(20), nullable=True, default='Low') # Store confidence level
    # --- End of Updated Fields ---
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Log {self.id} for {self.stock_ticker} on {self.predicted_date}>'