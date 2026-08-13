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
    PaymentSettings,
    Download,
    OrderStatus,
    PaymentStatus,
)


orders_bp = Blueprint("orders", __name__)


# ============================================================
# ALLOWED FILES
# ============================================================

ALLOWED_RECEIPT_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "pdf",
}


# ============================================================
# HELPERS
# ============================================================

def allowed_receipt(filename):
    if not filename:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in ALLOWED_RECEIPT_EXTENSIONS


def get_upload_folder():
    upload_folder = current_app.config.get("UPLOAD_FOLDER")

    if not upload_folder:
        upload_folder = os.path.join(
            current_app.root_path,
            "uploads"
        )

    os.makedirs(upload_folder, exist_ok=True)

    return upload_folder


def get_config_folder():
    config_folder = os.path.join(
        get_upload_folder(),
        "configs"
    )

    os.makedirs(config_folder, exist_ok=True)

    return config_folder


def get_receipt_folder():
    receipt_folder = os.path.join(
        get_upload_folder(),
        "receipts"
    )

    os.makedirs(receipt_folder, exist_ok=True)

    return receipt_folder


# ============================================================
# MY ORDERS
# ============================================================

@orders_bp.route("/orders", methods=["GET"])
@login_required
def order_list():

    orders = (
        Order.query
        .filter(
            Order.user_id == current_user.id
        )
        .order_by(
            Order.created_at.desc()
        )
        .all()
    )

    return render_template(
        "orders.html",
        orders=orders
    )


# ============================================================
# CHECKOUT
# ============================================================

@orders_bp.route("/checkout/<slug>", methods=["GET"])
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

    existing_paid = (
        Order.query
        .filter(
            Order.user_id == current_user.id,
            Order.config_id == config.id,
            Order.status == OrderStatus.PAID.value
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

    # --------------------------------------------------------
    # PAID ORDER
    # --------------------------------------------------------

    existing_paid = (
        Order.query
        .filter(
            Order.user_id == current_user.id,
            Order.config_id == config.id,
            Order.status == OrderStatus.PAID.value
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

    # --------------------------------------------------------
    # EXISTING PENDING ORDER
    # --------------------------------------------------------

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
        .order_by(
            Order.created_at.desc()
        )
        .first()
    )

    if existing_pending:

        return redirect(
            url_for(
                "orders.payment",
                order_id=existing_pending.id
            )
        )

    # --------------------------------------------------------
    # CREATE ORDER
    # --------------------------------------------------------

    order = Order(
        user_id=current_user.id,
        config_id=config.id,
        amount=config.price,
        status=OrderStatus.PENDING_PAYMENT.value,
    )

    db.session.add(order)
    db.session.flush()

    # --------------------------------------------------------
    # CREATE PAYMENT
    # --------------------------------------------------------

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

@orders_bp.route(
    "/payment/<int:order_id>",
    methods=["GET"]
)
@login_required
def payment(order_id):

    order = (
        Order.query
        .filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        )
        .first_or_404()
    )

    # --------------------------------------------------------
    # ALREADY PAID
    # --------------------------------------------------------

    if order.status == OrderStatus.PAID.value:

        flash(
            "Bu order allaqachon to'langan.",
            "success"
        )

        return redirect(
            url_for("orders.order_list")
        )

    # --------------------------------------------------------
    # PAYMENT
    # --------------------------------------------------------

    payment = order.payment

    if not payment:

        payment = Payment(
            order_id=order.id,
            provider="manual",
            status=PaymentStatus.PENDING.value,
        )

        db.session.add(payment)
        db.session.commit()

    # --------------------------------------------------------
    # PAYMENT SETTINGS
    # --------------------------------------------------------

    payment_settings = (
        PaymentSettings.query.first()
    )

    # --------------------------------------------------------
    # PAYMENT PAGE
    # --------------------------------------------------------

    return render_template(
        "payment.html",
        order=order,
        payment=payment,
        payment_settings=payment_settings
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
        .filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        )
        .first_or_404()
    )

    # --------------------------------------------------------
    # ALREADY PAID
    # --------------------------------------------------------

    if order.status == OrderStatus.PAID.value:

        flash(
            "Bu order allaqachon tasdiqlangan.",
            "success"
        )

        return redirect(
            url_for("orders.order_list")
        )

    # --------------------------------------------------------
    # FILE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # PAYMENT
    # --------------------------------------------------------

    payment = order.payment

    if not payment:

        payment = Payment(
            order_id=order.id,
            provider="manual",
            status=PaymentStatus.PENDING.value,
        )

        db.session.add(payment)
        db.session.flush()

    # --------------------------------------------------------
    # OLD RECEIPT
    # --------------------------------------------------------

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

                current_app.logger.warning(
                    "Old receipt o'chirilmadi: %s",
                    old_path
                )

        db.session.delete(old_receipt)
        db.session.flush()

    # --------------------------------------------------------
    # SAVE RECEIPT
    # --------------------------------------------------------

    original_name = secure_filename(
        file.filename
    )

    extension = ""

    if "." in original_name:

        extension = (
            "."
            + original_name.rsplit(
                ".",
                1
            )[1].lower()
        )

    filename = (
        uuid.uuid4().hex
        + extension
    )

    receipt_folder = get_receipt_folder()

    file_path = os.path.join(
        receipt_folder,
        filename
    )

    file.save(file_path)

    # --------------------------------------------------------
    # DATABASE RECEIPT
    # --------------------------------------------------------

    receipt = PaymentReceipt(
        payment_id=payment.id,
        filename=filename,
    )

    db.session.add(receipt)

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    payment.status = (
        PaymentStatus.UNDER_REVIEW.value
    )

    order.status = (
        OrderStatus.UNDER_REVIEW.value
    )

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
    "/download/<int:order_id>",
    methods=["GET"]
)
@login_required
def download(order_id):

    order = (
        Order.query
        .filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        )
        .first()
    )

    if not order:

        abort(404)

    # --------------------------------------------------------
    # PAID
    # --------------------------------------------------------

    if order.status != OrderStatus.PAID.value:

        flash(
            "Configni yuklab olish uchun to'lov tasdiqlanishi kerak.",
            "warning"
        )

        return redirect(
            url_for("orders.order_list")
        )

    # --------------------------------------------------------
    # CONFIG
    # --------------------------------------------------------

    config = order.config

    if not config:

        current_app.logger.error(
            "Order %s config topilmadi.",
            order.id
        )

        flash(
            "Ushbu orderga tegishli config topilmadi.",
            "danger"
        )

        return redirect(
            url_for("orders.order_list")
        )

    filename = config.cfg_file_filename

    if not filename:

        flash(
            "Config fayli mavjud emas.",
            "danger"
        )

        return redirect(
            url_for("orders.order_list")
        )

    # --------------------------------------------------------
    # SAFE FILENAME
    # --------------------------------------------------------

    safe_filename = os.path.basename(
        filename
    )

    if not safe_filename:

        abort(404)

    config_folder = get_config_folder()

    file_path = os.path.abspath(
        os.path.join(
            config_folder,
            safe_filename
        )
    )

    folder_path = os.path.abspath(
        config_folder
    )

    # --------------------------------------------------------
    # PATH TRAVERSAL
    # --------------------------------------------------------

    if not (
        file_path == folder_path
        or file_path.startswith(
            folder_path + os.sep
        )
    ):

        abort(404)

    # --------------------------------------------------------
    # FILE EXISTS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # DOWNLOAD LOG
    # --------------------------------------------------------

    download_log = Download(
        order_id=order.id,
        user_id=current_user.id,
        ip_address=request.headers.get(
            "X-Forwarded-For",
            request.remote_addr
        ),
    )

    db.session.add(download_log)
    db.session.commit()

    # --------------------------------------------------------
    # DOWNLOAD NAME
    # --------------------------------------------------------

    download_name = secure_filename(
        config.name
    )

    if not download_name:

        download_name = "config"

    if not download_name.lower().endswith(".cfg"):

        download_name += ".cfg"

    # --------------------------------------------------------
    # SEND FILE
    # --------------------------------------------------------

    return send_from_directory(
        config_folder,
        safe_filename,
        as_attachment=True,
        download_name=download_name
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
        .filter(
            Order.id == order_id,
            Order.user_id == current_user.id
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

    order.status = (
        OrderStatus.CANCELLED.value
    )

    if order.payment:

        order.payment.status = (
            PaymentStatus.REJECTED.value
        )

    db.session.commit()

    flash(
        "Order bekor qilindi.",
        "success"
    )

    return redirect(
        url_for("orders.order_list")
    )
