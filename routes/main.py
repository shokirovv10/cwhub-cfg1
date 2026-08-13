import os

from flask import (
    Blueprint,
    render_template,
    send_from_directory,
    current_app,
    abort,
)

from app.models import Config, Category


main_bp = Blueprint("main", __name__)


# =========================================================
# SCREENSHOTS
# =========================================================

@main_bp.route("/media/screenshots/<path:filename>")
def screenshot(filename):
    """
    Config screenshotlarini ommaga ko'rsatish.
    """

    folder = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        current_app.config["SCREENSHOTS_SUBDIR"],
    )

    safe_path = os.path.abspath(
        os.path.join(folder, filename)
    )

    base_folder = os.path.abspath(folder)

    if (
        not safe_path.startswith(base_folder)
        or not os.path.isfile(safe_path)
    ):
        abort(404)

    return send_from_directory(folder, filename)


# =========================================================
# AVATARS
# =========================================================

@main_bp.route("/media/avatars/<path:filename>")
def avatar(filename):
    """
    Foydalanuvchi avatarlari.
    """

    folder = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        current_app.config["AVATARS_SUBDIR"],
    )

    safe_path = os.path.abspath(
        os.path.join(folder, filename)
    )

    base_folder = os.path.abspath(folder)

    if (
        not safe_path.startswith(base_folder)
        or not os.path.isfile(safe_path)
    ):
        abort(404)

    return send_from_directory(folder, filename)


# =========================================================
# HOME PAGE
# =========================================================

@main_bp.route("/")
def index():

    latest = (
        Config.query
        .filter_by(
            is_active=True,
            is_hidden=False
        )
        .order_by(
            Config.created_at.desc()
        )
        .limit(4)
        .all()
    )

    top_sellers = (
        Config.query
        .filter_by(
            is_active=True,
            is_hidden=False
        )
        .order_by(
            Config.sales_count.desc()
        )
        .limit(4)
        .all()
    )

    premium = (
        Config.query
        .filter_by(
            is_active=True,
            is_hidden=False
        )
        .order_by(
            Config.price.desc()
        )
        .limit(4)
        .all()
    )

    categories = Category.query.all()

    return render_template(
        "index.html",
        latest=latest,
        top_sellers=top_sellers,
        premium=premium,
        categories=categories,
    )


# =========================================================
# ABOUT
# =========================================================

@main_bp.route("/about")
def about():
    """
    Biz haqda sahifasi.
    """

    return render_template("about.html")


# =========================================================
# SUPPORT
# =========================================================

@main_bp.route("/support")
def support():
    """
    Foydalanuvchilar uchun Support sahifasi.
    """

    return render_template("support.html")
