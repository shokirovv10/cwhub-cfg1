import os
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    send_file, abort
)
from flask_login import login_required, current_user

from app.extensions import db, limiter
from app.models import Config, Order, OrderStatus, PaymentSettings, Download, now_utc
from app.forms import ReceiptUploadForm
from services import payment_service
from services.file_service import save_uploaded_file, safe_upload_path

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/checkout/<slug>", methods=["GET", "POST"])
@login_required
def checkout(slug):
    config = Config.query.filter_by(slug=slug, is_active=True).first_or_404()

    if current_user.has_purchased(config.id):
        flash("Siz bu configni allaqachon sotib olgansiz.", "info")
        return redirect(url_for("configs.config_detail", slug=slug))

    # Agar oldin yaratilgan, hali to'lanmagan buyurtma bo'lsa - o'shani qayta ishlatamiz
    existing_order = Order.query.filter_by(
        user_id=current_user.id, config_id=config.id
    ).filter(Order.status.in_([
        OrderStatus.PENDING_PAYMENT.value, OrderStatus.AWAITING_RECEIPT.value, OrderStatus.UNDER_REVIEW.value
    ])).first()

    if request.method == "POST" and not existing_order:
        order = Order(user_id=current_user.id, config_id=config.id, amount=config.price)
        db.session.add(order)
        db.session.commit()
        payment_service.create_payment(order, provider="manual")
        return redirect(url_for("orders.checkout_payment", order_id=order.id))

    if existing_order:
        return redirect(url_for("orders.checkout_payment", order_id=existing_order.id))

    return render_template("checkout.html", config=config)


@orders_bp.route("/checkout/order/<int:order_id>/payment", methods=["GET", "POST"])
@login_required
def checkout_payment(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)

    if order.status == OrderStatus.PAID.value:
        return redirect(url_for("orders.order_detail", order_id=order.id))

    settings = PaymentSettings.query.first()
    form = ReceiptUploadForm()

    if form.validate_on_submit():
        try:
            filename = save_uploaded_file(
                form.receipt.data, "receipts", {"jpg", "jpeg", "png", "pdf"},
                {"image/jpeg", "image/png", "application/pdf"},
            )
            payment_service.attach_receipt(order.payment, filename)
            flash("Chek muvaffaqiyatli yuborildi. To'lov admin tomonidan tekshirilmoqda.", "success")
            return redirect(url_for("orders.order_detail", order_id=order.id))
        except ValueError as e:
            flash(str(e), "danger")

    return render_template("checkout_payment.html", order=order, settings=settings, form=form)


@orders_bp.route("/orders")
@login_required
def order_list():
    orders = current_user.orders.order_by(Order.created_at.desc()).all()
    return render_template("orders.html", orders=orders)


@orders_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    return render_template("order_detail.html", order=order)


@orders_bp.route("/orders/<int:order_id>/download")
@login_required
@limiter.limit("999 per hour")
def download_config(order_id):
    """Himoyalangan yuklab olish: login, order egaligi va PAID statusi tekshiriladi."""
    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        abort(403)
    if order.status != OrderStatus.PAID.value:
        abort(403)
    if not current_user.has_purchased(order.config_id):
        abort(403)

    config = order.config
    try:
        file_path = safe_upload_path("configs", config.cfg_file_filename)
    except ValueError:
        abort(403)

    if not os.path.isfile(file_path):
        abort(404)

    log = Download(order_id=order.id, user_id=current_user.id, ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()

    download_name = f"{config.slug}.{config.cfg_file_filename.rsplit('.', 1)[-1]}"
    return send_file(file_path, as_attachment=True, download_name=download_name)
