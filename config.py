import os

# Get the absolute path of the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Set Flask configuration variables."""
    
    # General Config
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key_that_you_should_change')
    
    # Database
    # Use os.path.join to create a platform-independent path
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 
                                             'sqlite:///' + os.path.join(basedir, 'instance', 'app.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False