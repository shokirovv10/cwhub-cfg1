import os
import uuid

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
    current_app,
    abort,
)

from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (
    Config,
    Order,
    Payment,
    PaymentReceipt,
    Download,
    OrderStatus,
    PaymentStatus,
)


orders_bp = Blueprint("orders", __name__)

ALLOWED_RECEIPT_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "pdf",
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def allowed_receipt(filename):
    if not filename:
        return False

    if "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[1].lower()

    return ext in ALLOWED_RECEIPT_EXTENSIONS


def get_config_folder():
    """
    Config fayllari saqlanadigan papka.
    app/config.py yoki __init__.py ichida UPLOAD_FOLDER
    mavjud bo'lishi kerak.
    """

    upload_folder = current_app.config.get("UPLOAD_FOLDER")

    if not upload_folder:
        upload_folder = os.path.join(
            current_app.root_path,
            "uploads"
        )

    config_folder = os.path.join(
        upload_folder,
        "configs"
    )

    os.makedirs(config_folder, exist_ok=True)

    return config_folder


def get_receipt_folder():
    """
    To'lov cheklari saqlanadigan papka.
    """

    upload_folder = current_app.config.get("UPLOAD_FOLDER")

    if not upload_folder:
        upload_folder = os.path.join(
            current_app.root_path,
            "uploads"
        )

    receipt_folder = os.path.join(
        upload_folder,
        "receipts"
    )

    os.makedirs(receipt_folder, exist_ok=True)

    return receipt_folder


# ============================================================
# MY ORDERS
# ============================================================

@orders_bp.route("/orders")
@login_required
def order_list():

    orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return render_template(
        "orders.html",
        orders=orders
    )


# ============================================================
# CHECKOUT
# ============================================================

@orders_bp.route("/checkout/<slug>")
@login_required
def checkout(slug):

    config = (
        Config.query
        .filter_by(
            slug=slug,
            is_active=True,
            is_hidden=False
        )
        .first_or_404()
    )

    # Agar foydalanuvchi allaqachon sotib olgan bo'lsa
    if current_user.has_purchased(config.id):

        flash(
            "Siz bu configni allaqachon sotib olgansiz.",
            "info"
        )

        return redirect(
            url_for("orders.order_list")
        )

    return render_template(
        "checkout.html",
        config=config
    )


# ============================================================
# CREATE ORDER
# ============================================================

@orders_bp.route(
    "/checkout/<slug>/create",
    methods=["POST"]
)
@login_required
def create_order(slug):

    config = (
        Config.query
        .filter_by(
            slug=slug,
            is_active=True,
            is_hidden=False
        )
        .first_or_404()
    )

    # Bir xil configni qayta sotib olishni bloklash
    existing_paid = (
        Order.query
        .filter_by(
            user_id=current_user.id,
            config_id=config.id,
            status=OrderStatus.PAID.value
        )
        .first()
    )

    if existing_paid:

        flash(
            "Siz bu configni allaqachon sotib olgansiz.",
            "info"
        )

        return redirect(
            url_for("orders.order_list")
        )

    # Eski pending order mavjud bo'lsa
    existing_pending = (
        Order.query
        .filter(
            Order.user_id == current_user.id,
            Order.config_id == config.id,
            Order.status.in_([
                OrderStatus.PENDING_PAYMENT.value,
                OrderStatus.AWAITING_RECEIPT.value,
                OrderStatus.UNDER_REVIEW.value,
            ])
        )
        .order_by(Order.created_at.desc())
        .first()
    )

    if existing_pending:

        return redirect(
            url_for(
                "orders.payment",
                order_id=existing_pending.id
            )
        )

    # Yangi order
    order = Order(
        user_id=current_user.id,
        config_id=config.id,
        amount=config.price,
        status=OrderStatus.PENDING_PAYMENT.value,
    )

    db.session.add(order)
    db.session.flush()

    # Payment yaratish
    payment = Payment(
        order_id=order.id,
        provider="manual",
        status=PaymentStatus.PENDING.value,
    )

    db.session.add(payment)

    db.session.commit()

    return redirect(
        url_for(
            "orders.payment",
            order_id=order.id
        )
    )


# ============================================================
# PAYMENT PAGE
# ============================================================

@orders_bp.route("/payment/<int:order_id>")
@login_required
def payment(order_id):

    order = (
        Order.query
        .filter_by(
            id=order_id,
            user_id=current_user.id
        )
        .first_or_404()
    )

    if order.status == OrderStatus.PAID.value:

        flash(
            "Bu order allaqachon to'langan.",
            "success"
        )

        return redirect(
            url_for("orders.order_list")
        )

    payment = order.payment

    return render_template(
        "payment.html",
        order=order,
        payment=payment
    )


# ============================================================
# UPLOAD RECEIPT
# ============================================================

@orders_bp.route(
    "/payment/<int:order_id>/receipt",
    methods=["POST"]
)
@login_required
def upload_receipt(order_id):

    order = (
        Order.query
        .filter_by(
            id=order_id,
            user_id=current_user.id
        )
        .first_or_404()
    )

    # Paid bo'lsa yana chek kerak emas
    if order.status == OrderStatus.PAID.value:

        flash(
            "Bu order allaqachon tasdiqlangan.",
            "success"
        )

        return redirect(
            url_for("orders.order_list")
        )

    file = request.files.get("receipt")

    if not file:

        flash(
            "Chek faylini tanlang.",
            "danger"
        )

        return redirect(
            url_for(
                "orders.payment",
                order_id=order.id
            )
        )

    if not file.filename:

        flash(
            "Chek fayli tanlanmagan.",
            "danger"
        )

        return redirect(
            url_for(
                "orders.payment",
                order_id=order.id
            )
        )

    if not allowed_receipt(file.filename):

        flash(
            "Faqat JPG, JPEG, PNG, WEBP yoki PDF fayl yuklash mumkin.",
            "danger"
        )

        return redirect(
            url_for(
                "orders.payment",
                order_id=order.id
            )
        )

    # Payment mavjudligini tekshirish
    payment = order.payment

    if not payment:

        payment = Payment(
            order_id=order.id,
            provider="manual",
            status=PaymentStatus.PENDING.value,
        )

        db.session.add(payment)
        db.session.flush()

    # Eski receipt bo'lsa
    old_receipt = payment.receipt

    if old_receipt:

        old_path = os.path.join(
            get_receipt_folder(),
            old_receipt.filename
        )

        if os.path.isfile(old_path):

            try:
                os.remove(old_path)
            except OSError:
                pass

        db.session.delete(old_receipt)
        db.session.flush()

    # Random unique filename
    original_name = secure_filename(
        file.filename
    )

    extension = ""

    if "." in original_name:

        extension = (
            "." +
            original_name.rsplit(".", 1)[1].lower()
        )

    filename = (
        uuid.uuid4().hex +
        extension
    )

    receipt_folder = get_receipt_folder()

    file.save(
        os.path.join(
            receipt_folder,
            filename
        )
    )

    receipt = PaymentReceipt(
        payment_id=payment.id,
        filename=filename,
    )

    db.session.add(receipt)

    payment.status = PaymentStatus.UNDER_REVIEW.value

    order.status = OrderStatus.UNDER_REVIEW.value

    db.session.commit()

    flash(
        "Chek muvaffaqiyatli yuborildi. Admin tekshiradi.",
        "success"
    )

    return redirect(
        url_for("orders.order_list")
    )


# ============================================================
# DOWNLOAD CONFIG
# ============================================================

@orders_bp.route(
    "/download/<int:order_id>"
)
@login_required
def download(order_id):

    # Faqat o'z orderini topadi
    order = (
        Order.query
        .filter_by(
            id=order_id,
            user_id=current_user.id
        )
        .first()
    )

    if not order:

        abort(404)

    # Faqat PAID order yuklana oladi
    if order.status != OrderStatus.PAID.value:

        flash(
            "Configni yuklab olish uchun to'lov tasdiqlanishi kerak.",
            "warning"
        )

        return redirect(
            url_for("orders.order_list")
        )

    config = order.config

    if not config:

        abort(404)

    filename = config.cfg_file_filename

    if not filename:

        flash(
            "Config fayli mavjud emas.",
            "danger"
        )

        return redirect(
            url_for("orders.order_list")
        )

    config_folder = get_config_folder()

    # Faqat fayl nomidan foydalanamiz
    safe_filename = os.path.basename(filename)

    file_path = os.path.abspath(
        os.path.join(
            config_folder,
            safe_filename
        )
    )

    folder_path = os.path.abspath(
        config_folder
    )

    # Path traversal himoyasi
    if not (
        file_path == folder_path
        or file_path.startswith(
            folder_path + os.sep
        )
    ):

        abort(404)

    # Fayl mavjudligini tekshirish
    if not os.path.isfile(file_path):

        current_app.logger.error(
            "Config file not found: %s",
            file_path
        )

        flash(
            "Config fayli serverda topilmadi.",
            "danger"
        )

        return redirect(
            url_for("orders.order_list")
        )

    # Download log
    download_log = Download(
        order_id=order.id,
        user_id=current_user.id,
        ip_address=request.headers.get(
            "X-Forwarded-For",
            request.remote_addr
        ),
    )

    db.session.add(download_log)

    # Sales countni bu yerda oshirmaymiz.
    # Sotuv tasdiqlanganda oshirilishi kerak.

    db.session.commit()

    # Original filenameni download uchun berish
    download_name = secure_filename(
        config.name
    )

    if not download_name:

        download_name = "config"

    if not download_name.lower().endswith(".cfg"):

        download_name += ".cfg"

    return send_from_directory(
        config_folder,
        safe_filename,
        as_attachment=True,
        download_name=download_name,
    )


# ============================================================
# CANCEL ORDER
# ============================================================

@orders_bp.route(
    "/orders/<int:order_id>/cancel",
    methods=["POST"]
)
@login_required
def cancel_order(order_id):

    order = (
        Order.query
        .filter_by(
            id=order_id,
            user_id=current_user.id
        )
        .first_or_404()
    )

    if order.status in [
        OrderStatus.PAID.value,
        OrderStatus.UNDER_REVIEW.value,
    ]:

        flash(
            "Bu orderni bekor qilib bo'lmaydi.",
            "warning"
        )

        return redirect(
            url_for("orders.order_list")
        )

    order.status = OrderStatus.CANCELLED.value

    if order.payment:

        order.payment.status = PaymentStatus.REJECTED.value

    db.session.commit()

    flash(
        "Order bekor qilindi.",
        "success"
    )

    return redirect(
        url_for("orders.order_list")
    )
