import re
import uuid
import os

from datetime import datetime, timezone

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    abort,
    send_file,
)

from flask_login import login_required, current_user

from app.extensions import db

from app.models import (
    User,
    Config,
    Category,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Review,
    PaymentSettings,
    SiteSettings,
    Admin,
    SupportMessage,
)

from app.forms import (
    ConfigForm,
    CategoryForm,
    PaymentSettingsForm,
    SiteSettingsForm,
    RejectOrderForm,
)

from services import payment_service

from services.file_service import (
    save_uploaded_file,
    safe_upload_path,
)


# ===========================================================================
# ADMIN BLUEPRINT
# ===========================================================================

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


# ===========================================================================
# HELPERS
# ===========================================================================

def slugify(text: str) -> str:

    text = text.lower().strip()

    text = re.sub(
        r"[^a-z0-9\-]+",
        "-",
        text
    )

    text = re.sub(
        r"-+",
        "-",
        text
    ).strip("-")

    return text or uuid.uuid4().hex[:8]


# ===========================================================================
# ADMIN ACCESS
# ===========================================================================

@admin_bp.before_request
@login_required
def _require_admin():

    if not current_user.is_admin:
        abort(403)


# ===========================================================================
# DASHBOARD
# ===========================================================================

@admin_bp.route("/")
def dashboard():

    stats = {

        "users": User.query.count(),

        "configs": Config.query.count(),

        "orders": Order.query.count(),

        "paid_orders": Order.query.filter_by(
            status=OrderStatus.PAID.value
        ).count(),

        "pending_payments": Order.query.filter_by(
            status=OrderStatus.UNDER_REVIEW.value
        ).count(),

        "rejected_payments": Order.query.filter_by(
            status=OrderStatus.REJECTED.value
        ).count(),
    }

    paid_orders = Order.query.filter_by(
        status=OrderStatus.PAID.value
    ).all()

    stats["total_revenue"] = sum(
        float(order.amount)
        for order in paid_orders
    )

    recent_orders = Order.query.order_by(
        Order.created_at.desc()
    ).limit(8).all()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_orders=recent_orders
    )


# ===========================================================================
# CONFIGS
# ===========================================================================

@admin_bp.route("/configs")
def config_list():

    configs = Config.query.order_by(
        Config.created_at.desc()
    ).all()

    return render_template(
        "admin/configs.html",
        configs=configs
    )


@admin_bp.route(
    "/configs/new",
    methods=["GET", "POST"]
)
def config_new():

    form = ConfigForm()

    form.category_id.choices = [
        (c.id, c.name)
        for c in Category.query.all()
    ]

    if form.validate_on_submit():

        if not form.cfg_file.data:

            flash(
                "CFG fayl majburiy.",
                "danger"
            )

            return render_template(
                "admin/config_form.html",
                form=form,
                mode="new"
            )

        try:

            cfg_filename = save_uploaded_file(
                form.cfg_file.data,
                "configs",
                {"cfg", "zip"},
                {
                    "text/plain",
                    "application/zip",
                    "application/x-zip-compressed",
                    "application/octet-stream",
                },
            )

            screenshot_filename = None

            if form.screenshot.data:

                screenshot_filename = save_uploaded_file(
                    form.screenshot.data,
                    "screenshots",
                    {
                        "jpg",
                        "jpeg",
                        "png",
                        "webp",
                    },
                    {
                        "image/jpeg",
                        "image/png",
                        "image/webp",
                    },
                )

            base_slug = slugify(
                form.name.data
            )

            slug = base_slug
            n = 1

            while Config.query.filter_by(
                slug=slug
            ).first():

                n += 1

                slug = f"{base_slug}-{n}"

            config = Config(
                name=form.name.data,
                slug=slug,
                description=form.description.data,
                features=form.features.data,
                price=form.price.data,
                category_id=form.category_id.data,
                author=form.author.data,
                cs_version=form.cs_version.data,
                demo_video_url=form.demo_video_url.data,
                cfg_file_filename=cfg_filename,
                screenshot_filename=screenshot_filename,
                is_active=form.is_active.data,
                is_hidden=form.is_hidden.data,
            )

            db.session.add(config)

            db.session.commit()

            flash(
                "Config qo'shildi.",
                "success"
            )

            return redirect(
                url_for("admin.config_list")
            )

        except ValueError as e:

            flash(
                str(e),
                "danger"
            )

    return render_template(
        "admin/config_form.html",
        form=form,
        mode="new"
    )


@admin_bp.route(
    "/configs/<int:config_id>/edit",
    methods=["GET", "POST"]
)
def config_edit(config_id):

    config = Config.query.get_or_404(
        config_id
    )

    form = ConfigForm(
        obj=config
    )

    form.category_id.choices = [
        (c.id, c.name)
        for c in Category.query.all()
    ]

    if request.method == "GET":

        form.category_id.data = (
            config.category_id
        )

    if form.validate_on_submit():

        try:

            config.name = form.name.data
            config.description = form.description.data
            config.features = form.features.data
            config.price = form.price.data
            config.category_id = form.category_id.data
            config.author = form.author.data
            config.cs_version = form.cs_version.data
            config.demo_video_url = form.demo_video_url.data
            config.is_active = form.is_active.data
            config.is_hidden = form.is_hidden.data

            if form.cfg_file.data:

                config.cfg_file_filename = (
                    save_uploaded_file(
                        form.cfg_file.data,
                        "configs",
                        {"cfg", "zip"},
                        {
                            "text/plain",
                            "application/zip",
                            "application/x-zip-compressed",
                            "application/octet-stream",
                        },
                    )
                )

            if form.screenshot.data:

                config.screenshot_filename = (
                    save_uploaded_file(
                        form.screenshot.data,
                        "screenshots",
                        {
                            "jpg",
                            "jpeg",
                            "png",
                            "webp",
                        },
                        {
                            "image/jpeg",
                            "image/png",
                            "image/webp",
                        },
                    )
                )

            db.session.commit()

            flash(
                "Config yangilandi.",
                "success"
            )

            return redirect(
                url_for("admin.config_list")
            )

        except ValueError as e:

            flash(
                str(e),
                "danger"
            )

    return render_template(
        "admin/config_form.html",
        form=form,
        mode="edit",
        config=config
    )


@admin_bp.route(
    "/configs/<int:config_id>/delete",
    methods=["POST"]
)
def config_delete(config_id):

    config = Config.query.get_or_404(
        config_id
    )

    db.session.delete(config)

    db.session.commit()

    flash(
        "Config o'chirildi.",
        "info"
    )

    return redirect(
        url_for("admin.config_list")
    )


@admin_bp.route(
    "/configs/<int:config_id>/toggle-hide",
    methods=["POST"]
)
def config_toggle_hide(config_id):

    config = Config.query.get_or_404(
        config_id
    )

    config.is_hidden = not config.is_hidden

    db.session.commit()

    return redirect(
        url_for("admin.config_list")
    )


@admin_bp.route(
    "/configs/<int:config_id>/toggle-active",
    methods=["POST"]
)
def config_toggle_active(config_id):

    config = Config.query.get_or_404(
        config_id
    )

    config.is_active = not config.is_active

    db.session.commit()

    return redirect(
        url_for("admin.config_list")
    )


# ===========================================================================
# CATEGORIES
# ===========================================================================

@admin_bp.route(
    "/categories",
    methods=["GET", "POST"]
)
def categories():

    form = CategoryForm()

    if form.validate_on_submit():

        slug = slugify(
            form.name.data
        )

        if Category.query.filter_by(
            slug=slug
        ).first():

            flash(
                "Bu kategoriya allaqachon mavjud.",
                "danger"
            )

        else:

            category = Category(
                name=form.name.data,
                slug=slug
            )

            db.session.add(category)

            db.session.commit()

            flash(
                "Kategoriya qo'shildi.",
                "success"
            )

            return redirect(
                url_for("admin.categories")
            )

    all_categories = Category.query.all()

    return render_template(
        "admin/categories.html",
        form=form,
        categories=all_categories
    )


@admin_bp.route(
    "/categories/<int:cat_id>/delete",
    methods=["POST"]
)
def category_delete(cat_id):

    cat = Category.query.get_or_404(
        cat_id
    )

    if cat.configs.count() > 0:

        flash(
            "Bu kategoriyada configlar mavjud, avval ularni ko'chiring yoki o'chiring.",
            "danger"
        )

    else:

        db.session.delete(cat)

        db.session.commit()

        flash(
            "Kategoriya o'chirildi.",
            "info"
        )

    return redirect(
        url_for("admin.categories")
    )


# ===========================================================================
# USERS
# ===========================================================================

@admin_bp.route("/users")
def users():

    q = request.args.get(
        "q",
        ""
    ).strip()

    query = User.query

    if q:

        like = f"%{q}%"

        query = query.filter(
            db.or_(
                User.username.ilike(like),
                User.email.ilike(like)
            )
        )

    all_users = query.order_by(
        User.created_at.desc()
    ).all()

    return render_template(
        "admin/users.html",
        users=all_users,
        q=q
    )


# ===========================================================================
# USER DETAIL
# ===========================================================================

@admin_bp.route(
    "/users/<int:user_id>"
)
def user_detail(user_id):

    user = User.query.get_or_404(
        user_id
    )

    orders = user.orders.order_by(
        Order.created_at.desc()
    ).all()

    return render_template(
        "admin/user_detail.html",
        user=user,
        orders=orders
    )


# ===========================================================================
# MAKE ADMIN
# ===========================================================================

@admin_bp.route(
    "/users/<int:user_id>/make-admin",
    methods=["POST"]
)
def make_admin(user_id):

    user = User.query.get_or_404(
        user_id
    )

    if user.id == current_user.id:

        flash(
            "O'zingizni admin qila olmaysiz.",
            "warning"
        )

        return redirect(
            url_for("admin.users")
        )

    if user.is_admin:

        flash(
            "Bu foydalanuvchi allaqachon admin.",
            "warning"
        )

        return redirect(
            url_for("admin.users")
        )

    admin = Admin(
        user_id=user.id,
        is_super_admin=False
    )

    db.session.add(admin)

    db.session.commit()

    flash(
        f"{user.username} ga Admin huquqi berildi.",
        "success"
    )

    return redirect(
        url_for("admin.users")
    )


# ===========================================================================
# REMOVE ADMIN
# ===========================================================================

@admin_bp.route(
    "/users/<int:user_id>/remove-admin",
    methods=["POST"]
)
def remove_admin(user_id):

    user = User.query.get_or_404(
        user_id
    )

    if user.id == current_user.id:

        flash(
            "O'zingizning adminligingizni olib tashlay olmaysiz.",
            "danger"
        )

        return redirect(
            url_for("admin.users")
        )

    admin = Admin.query.filter_by(
        user_id=user.id
    ).first()

    if not admin:

        flash(
            "Bu foydalanuvchi admin emas.",
            "warning"
        )

        return redirect(
            url_for("admin.users")
        )

    db.session.delete(admin)

    db.session.commit()

    flash(
        f"{user.username} adminlikdan olib tashlandi.",
        "info"
    )

    return redirect(
        url_for("admin.users")
    )


# ===========================================================================
# MAKE SUPER ADMIN
# ===========================================================================

@admin_bp.route(
    "/users/<int:user_id>/make-super-admin",
    methods=["POST"]
)
def make_super_admin(user_id):

    user = User.query.get_or_404(
        user_id
    )

    if user.id == current_user.id:

        flash(
            "O'zingizni Super Admin qila olmaysiz.",
            "warning"
        )

        return redirect(
            url_for("admin.users")
        )

    admin = Admin.query.filter_by(
        user_id=user.id
    ).first()

    if not admin:

        admin = Admin(
            user_id=user.id,
            is_super_admin=True
        )

        db.session.add(admin)

    else:

        admin.is_super_admin = True

    db.session.commit()

    flash(
        f"{user.username} Super Admin qilindi.",
        "success"
    )

    return redirect(
        url_for("admin.users")
    )


# ===========================================================================
# REMOVE SUPER ADMIN
# ===========================================================================

@admin_bp.route(
    "/users/<int:user_id>/remove-super-admin",
    methods=["POST"]
)
def remove_super_admin(user_id):

    user = User.query.get_or_404(
        user_id
    )

    if user.id == current_user.id:

        flash(
            "O'zingizning Super Adminligingizni olib tashlay olmaysiz.",
            "danger"
        )

        return redirect(
            url_for("admin.users")
        )

    admin = Admin.query.filter_by(
        user_id=user.id
    ).first()

    if not admin:

        flash(
            "Bu foydalanuvchi admin emas.",
            "warning"
        )

        return redirect(
            url_for("admin.users")
        )

    admin.is_super_admin = False

    db.session.commit()

    flash(
        f"{user.username} oddiy Admin darajasiga tushirildi.",
        "info"
    )

    return redirect(
        url_for("admin.users")
    )


# ===========================================================================
# BLOCK / UNBLOCK
# ===========================================================================

@admin_bp.route(
    "/users/<int:user_id>/toggle-block",
    methods=["POST"]
)
def user_toggle_block(user_id):

    user = User.query.get_or_404(
        user_id
    )

    if user.is_admin:

        flash(
            "Adminlarni bloklab bo'lmaydi.",
            "danger"
        )

        return redirect(
            url_for("admin.users")
        )

    user.is_blocked = not user.is_blocked

    db.session.commit()

    if user.is_blocked:

        flash(
            f"{user.username} bloklandi.",
            "warning"
        )

    else:

        flash(
            f"{user.username} blokdan chiqarildi.",
            "success"
        )

    return redirect(
        url_for("admin.users")
    )


# ===========================================================================
# ORDERS
# ===========================================================================

@admin_bp.route("/orders")
def order_list():

    status = request.args.get(
        "status",
        ""
    )

    query = Order.query

    if status:

        query = query.filter_by(
            status=status
        )

    all_orders = query.order_by(
        Order.created_at.desc()
    ).all()

    return render_template(
        "admin/orders.html",
        orders=all_orders,
        status=status,
        statuses=[
            s.value
            for s in OrderStatus
        ]
    )


# ===========================================================================
# PAYMENT RECEIPT
# ===========================================================================

@admin_bp.route(
    "/payments/<int:order_id>/receipt"
)
def view_receipt(order_id):

    order = Order.query.get_or_404(
        order_id
    )

    if (
        not order.payment
        or not order.payment.receipt
    ):

        abort(404)

    try:

        file_path = safe_upload_path(
            "receipts",
            order.payment.receipt.filename
        )

    except ValueError:

        abort(403)

    if not os.path.isfile(file_path):

        abort(404)

    return send_file(
        file_path
    )


# ===========================================================================
# PAYMENTS
# ===========================================================================

@admin_bp.route("/payments")
def payments():

    pending = Order.query.filter_by(
        status=OrderStatus.UNDER_REVIEW.value
    ).order_by(
        Order.created_at.asc()
    ).all()

    reject_form = RejectOrderForm()

    return render_template(
        "admin/payments.html",
        orders=pending,
        reject_form=reject_form
    )


@admin_bp.route(
    "/payments/<int:order_id>/approve",
    methods=["POST"]
)
def payment_approve(order_id):

    order = Order.query.get_or_404(
        order_id
    )

    if not order.payment:

        flash(
            "Bu order uchun to'lov topilmadi.",
            "danger"
        )

        return redirect(
            url_for("admin.payments")
        )

    payment_service.approve_payment(
        order.payment,
        current_user.admin_profile.id
    )

    flash(
        f"Order #{order.id} tasdiqlandi. Foydalanuvchi endi yuklab olishi mumkin.",
        "success"
    )

    return redirect(
        url_for("admin.payments")
    )


@admin_bp.route(
    "/payments/<int:order_id>/reject",
    methods=["POST"]
)
def payment_reject(order_id):

    order = Order.query.get_or_404(
        order_id
    )

    form = RejectOrderForm()

    if not order.payment:

        flash(
            "Bu order uchun to'lov topilmadi.",
            "danger"
        )

        return redirect(
            url_for("admin.payments")
        )

    reason = (
        form.reason.data
        if form.validate_on_submit()
        else request.form.get(
            "reason",
            ""
        )
    )

    payment_service.reject_payment(
        order.payment,
        current_user.admin_profile.id,
        reason=reason
    )

    flash(
        f"Order #{order.id} rad etildi.",
        "info"
    )

    return redirect(
        url_for("admin.payments")
    )


# ===========================================================================
# REVIEWS
# ===========================================================================

@admin_bp.route("/reviews")
def reviews():

    all_reviews = Review.query.order_by(
        Review.created_at.desc()
    ).all()

    return render_template(
        "admin/reviews.html",
        reviews=all_reviews
    )


@admin_bp.route(
    "/reviews/<int:review_id>/delete",
    methods=["POST"]
)
def review_delete(review_id):

    review = Review.query.get_or_404(
        review_id
    )

    db.session.delete(review)

    db.session.commit()

    flash(
        "Review o'chirildi.",
        "info"
    )

    return redirect(
        url_for("admin.reviews")
    )


# ===========================================================================
# SUPPORT
# ===========================================================================

@admin_bp.route("/support")
def support():

    messages = SupportMessage.query.order_by(
        SupportMessage.created_at.desc()
    ).all()

    return render_template(
        "admin/support.html",
        messages=messages
    )


# ---------------------------------------------------------------------------
# SUPPORT REPLY
# ---------------------------------------------------------------------------

@admin_bp.route(
    "/support/<int:message_id>/reply",
    methods=["POST"]
)
def support_reply(message_id):

    message = SupportMessage.query.get_or_404(
        message_id
    )

    reply = request.form.get(
        "reply",
        ""
    ).strip()

    if not reply:

        flash(
            "Javob matni bo'sh bo'lishi mumkin emas.",
            "danger"
        )

        return redirect(
            url_for("admin.support")
        )

    message.admin_reply = reply

    message.replied_by_admin_id = (
        current_user.id
    )

    message.replied_at = datetime.now(
        timezone.utc
    )

    db.session.commit()

    flash(
        "Support xabariga javob yuborildi.",
        "success"
    )

    return redirect(
        url_for("admin.support")
    )


# ---------------------------------------------------------------------------
# SUPPORT DELETE
# ---------------------------------------------------------------------------

@admin_bp.route(
    "/support/<int:message_id>/delete",
    methods=["POST"]
)
def support_delete(message_id):

    message = SupportMessage.query.get_or_404(
        message_id
    )

    db.session.delete(message)

    db.session.commit()

    flash(
        "Support xabari o'chirildi.",
        "info"
    )

    return redirect(
        url_for("admin.support")
    )


# ===========================================================================
# SETTINGS
# ===========================================================================

@admin_bp.route(
    "/settings/payment",
    methods=["GET", "POST"]
)
def payment_settings():

    settings = PaymentSettings.query.first()

    if not settings:

        settings = PaymentSettings()

        db.session.add(settings)

        db.session.commit()

    form = PaymentSettingsForm(
        obj=settings
    )

    if form.validate_on_submit():

        form.populate_obj(
            settings
        )

        db.session.commit()

        flash(
            "To'lov sozlamalari yangilandi.",
            "success"
        )

        return redirect(
            url_for("admin.payment_settings")
        )

    return render_template(
        "admin/payment_settings.html",
        form=form
    )


@admin_bp.route(
    "/settings/site",
    methods=["GET", "POST"]
)
def site_settings():

    settings = SiteSettings.query.first()

    if not settings:

        settings = SiteSettings()

        db.session.add(settings)

        db.session.commit()

    form = SiteSettingsForm(
        obj=settings
    )

    if form.validate_on_submit():

        form.populate_obj(
            settings
        )

        db.session.commit()

        flash(
            "Sayt sozlamalari yangilandi.",
            "success"
        )

        return redirect(
            url_for("admin.site_settings")
        )

    return render_template(
        "admin/site_settings.html",
        form=form
    )
# ===========================================================================
# SUPPORT
# ===========================================================================

@admin_bp.route("/support")
def support():

    messages = SupportMessage.query.order_by(
        SupportMessage.created_at.asc()
    ).all()

    return render_template(
        "admin/support.html",
        messages=messages
    )


@admin_bp.route(
    "/support/<int:user_id>/reply",
    methods=["POST"]
)
def support_reply(user_id):

    user = User.query.get_or_404(user_id)

    message = request.form.get(
        "message",
        ""
    ).strip()

    if not message:
        flash(
            "Xabar bo'sh bo'lishi mumkin emas.",
            "danger"
        )

        return redirect(
            url_for(
                "admin.support"
            )
        )

    support_message = SupportMessage(
        user_id=user.id,
        message=message,
        is_from_admin=True,
        is_read=True
    )

    db.session.add(
        support_message
    )

    db.session.commit()

    flash(
        f"{user.username} ga javob yuborildi.",
        "success"
    )

    return redirect(
        url_for(
            "admin.support"
        )
    )


@admin_bp.route(
    "/support/<int:message_id>/read",
    methods=["POST"]
)
def support_mark_read(message_id):

    message = SupportMessage.query.get_or_404(
        message_id
    )

    message.is_read = True

    db.session.commit()

    return redirect(
        url_for(
            "admin.support"
        )
    )


@admin_bp.route(
    "/support/<int:message_id>/delete",
    methods=["POST"]
)
def support_delete(message_id):

    message = SupportMessage.query.get_or_404(
        message_id
    )

    db.session.delete(
        message
    )

    db.session.commit()

    flash(
        "Support xabari o'chirildi.",
        "info"
    )

    return redirect(
        url_for(
            "admin.support"
        )
    )