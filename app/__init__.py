import os
from flask import Flask, render_template, request
from app.config import Config
from app.extensions import db, login_manager, csrf, limiter


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
    )
    app.config.from_object(config_class)

    # --- Extensions ---
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    app.config["RATELIMIT_STORAGE_URI"] = config_class.RATELIMIT_STORAGE_URI
    limiter.init_app(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    for sub in (app.config["CONFIGS_SUBDIR"], app.config["RECEIPTS_SUBDIR"],
                app.config["SCREENSHOTS_SUBDIR"], app.config["AVATARS_SUBDIR"]):
        os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], sub), exist_ok=True)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- Blueprints ---
    from routes.main import main_bp
    from routes.auth import auth_bp
    from routes.configs import configs_bp
    from routes.orders import orders_bp
    from routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(configs_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)

    # --- Security headers (asosiy XSS / clickjacking himoyasi) ---
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # --- Error handlers (bir xil dizaynda) ---
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/500.html", message="Fayl hajmi juda katta."), 413

    # --- Jinja globals ---
    from app.models import SiteSettings

    @app.context_processor
    def inject_globals():
        settings = SiteSettings.query.first()
        return {"site_settings": settings}

    return app
