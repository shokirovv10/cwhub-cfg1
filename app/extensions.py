"""
Kengaytmalar (extensions) shu yerda bir marta yaratiladi va
app/__init__.py ichida init_app() bilan bog'lanadi. Bu circular import'ni oldini oladi.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

login_manager.login_view = "auth.login"
login_manager.login_message = "Davom etish uchun tizimga kiring."
login_manager.login_message_category = "warning"
