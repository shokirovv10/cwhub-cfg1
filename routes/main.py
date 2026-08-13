import os
from flask import Blueprint, render_template, send_from_directory, current_app, abort
from app.models import Config, Category

main_bp = Blueprint("main", __name__)


@main_bp.route("/media/screenshots/<path:filename>")
def screenshot(filename):
    """Config screenshotlari (marketing rasm) - ommaviy ko'rish uchun ochiq.
    Bu cfg fayllardan farqli o'laroq himoyalanmagan, chunki reklama maqsadida ko'rsatiladi."""
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], current_app.config["SCREENSHOTS_SUBDIR"])
    safe_path = os.path.abspath(os.path.join(folder, filename))
    if not safe_path.startswith(os.path.abspath(folder)) or not os.path.isfile(safe_path):
        abort(404)
    return send_from_directory(folder, filename)


@main_bp.route("/media/avatars/<path:filename>")
def avatar(filename):
    """Foydalanuvchi avatarlari - ommaviy ko'rish uchun ochiq."""
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], current_app.config["AVATARS_SUBDIR"])
    safe_path = os.path.abspath(os.path.join(folder, filename))
    if not safe_path.startswith(os.path.abspath(folder)) or not os.path.isfile(safe_path):
        abort(404)
    return send_from_directory(folder, filename)


@main_bp.route("/")
def index():
    latest = Config.query.filter_by(is_active=True, is_hidden=False).order_by(Config.created_at.desc()).limit(4).all()
    top_sellers = Config.query.filter_by(is_active=True, is_hidden=False).order_by(Config.sales_count.desc()).limit(4).all()
    premium = Config.query.filter_by(is_active=True, is_hidden=False).order_by(Config.price.desc()).limit(4).all()
    categories = Category.query.all()
    return render_template(
        "index.html",
        latest=latest, top_sellers=top_sellers, premium=premium, categories=categories,
    )


@main_bp.route("/about")
def about():
    return render_template("about.html")
