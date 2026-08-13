from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import SupportMessage


support_bp = Blueprint(
    "support",
    __name__,
    url_prefix="/support"
)


@support_bp.route("/", methods=["GET", "POST"])
@login_required
def index():

    if request.method == "POST":

        message = request.form.get("message", "").strip()

        if not message:
            flash("Xabar bo'sh bo'lishi mumkin emas.", "danger")
            return redirect(url_for("support.index"))

        support_message = SupportMessage(
            user_id=current_user.id,
            message=message,
            is_from_admin=False,
            is_read=False
        )

        db.session.add(support_message)
        db.session.commit()

        flash(
            "Xabaringiz supportga yuborildi.",
            "success"
        )

        return redirect(
            url_for("support.index")
        )

    messages = SupportMessage.query.filter_by(
        user_id=current_user.id
    ).order_by(
        SupportMessage.created_at.asc()
    ).all()

    return render_template(
        "support.html",
        messages=messages
    )