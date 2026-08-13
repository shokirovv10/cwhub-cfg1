import os

from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    send_file,
    abort,
    current_app,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.models import (
    Config,
    Category,
    Review,
    Download,
    Order,
    OrderStatus,
)
from app.forms import ReviewForm


configs_bp = Blueprint("configs", __name__)

PER_PAGE = 9


# ============================================================
# CONFIGLAR RO'YXATI
# ============================================================

@configs_bp.route("/configs")
def config_list():

    q = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    sort = request.args.get("sort", "newest")
    page = request.args.get("page", 1, type=int)

    query = Config.query.filter_by(
        is_active=True,
        is_hidden=False
    )

    # QIDIRUV
    if q:

        like = f"%{q}%"

        query = query.filter(
            db.or_(
                Config.name.ilike(like),
                Config.author.ilike(like)
            )
        )

    # KATEGORIYA
    if category_id:

        query = query.filter(
            Config.category_id == category_id
        )

    # SARALASH
    if sort == "price_asc":

        query = query.order_by(
            Config.price.asc()
        )

    elif sort == "price_desc":

        query = query.order_by(
            Config.price.desc()
        )

    elif sort == "bestselling":

        query = query.order_by(
            Config.sales_count.desc()
        )

    elif sort == "rating":

        # Rating property bo'lgani sababli
        # Python orqali saralanadi.
        query = query.order_by(
            Config.created_at.desc()
        )

    else:

        query = query.order_by(
            Config.created_at.desc()
        )

    # PAGINATION
    pagination = query.paginate(
        page=page,
        per_page=PER_PAGE,
        error_out=False
    )

    items = pagination.items

    # RATING BO'YICHA SARALASH
    if sort == "rating":

        items = sorted(
            items,
            key=lambda config: config.average_rating,
            reverse=True
        )

    categories = Category.query.all()

    return render_template(
        "configs.html",
        configs=items,
        pagination=pagination,
        categories=categories,
        q=q,
        category_id=category_id,
        sort=sort,
    )


# ============================================================
# CONFIG DETAIL
# ============================================================

@configs_bp.route("/config/<slug>")
def config_detail(slug):

    config = Config.query.filter_by(
        slug=slug,
        is_active=True,
        is_hidden=False
    ).first_or_404()

    already_purchased = False
    can_review = False

    if current_user.is_authenticated:

        already_purchased = current_user.has_purchased(
            config.id
        )

        has_reviewed = Review.query.filter_by(
            user_id=current_user.id,
            config_id=config.id
        ).first()

        can_review = (
            already_purchased
            and not has_reviewed
        )

    reviews = config.reviews.order_by(
        Review.created_at.desc()
    ).all()

    review_form = ReviewForm()

    return render_template(
        "config_detail.html",
        config=config,
        already_purchased=already_purchased,
        reviews=reviews,
        can_review=can_review,
        review_form=review_form,
    )


# ============================================================
# CONFIG DOWNLOAD
# ============================================================

@configs_bp.route("/config/<slug>/download")
@login_required
def download_config(slug):

    # --------------------------------------------------------
    # CONFIGNI TOPISH
    # --------------------------------------------------------

    config = Config.query.filter_by(
        slug=slug,
        is_active=True,
        is_hidden=False
    ).first_or_404()

    # --------------------------------------------------------
    # SOTIB OLINGAN ORDERNI TOPISH
    # --------------------------------------------------------

    order = Order.query.filter_by(
        user_id=current_user.id,
        config_id=config.id,
        status=OrderStatus.PAID.value
    ).first()

    if not order:

        flash(
            "Bu configni yuklab olish uchun avval sotib olishingiz kerak.",
            "danger"
        )

        return redirect(
            url_for(
                "configs.config_detail",
                slug=slug
            )
        )

    # --------------------------------------------------------
    # FAYL NOMI
    # --------------------------------------------------------

    filename = config.cfg_file_filename

    if not filename:

        current_app.logger.error(
            "Config uchun cfg_file_filename mavjud emas. Config ID: %s",
            config.id
        )

        flash(
            "Config fayli topilmadi.",
            "danger"
        )

        return redirect(
            url_for(
                "configs.config_detail",
                slug=slug
            )
        )

    # --------------------------------------------------------
    # CONFIG UPLOAD PAPKASI
    # --------------------------------------------------------

    upload_folder = current_app.config.get(
        "UPLOAD_FOLDER"
    )

    if not upload_folder:

        current_app.logger.error(
            "UPLOAD_FOLDER konfiguratsiyada mavjud emas."
        )

        flash(
            "Server konfiguratsiyasida xatolik.",
            "danger"
        )

        return redirect(
            url_for(
                "configs.config_detail",
                slug=slug
            )
        )

    configs_subdir = current_app.config.get(
        "CONFIGS_SUBDIR",
        "configs"
    )

    configs_folder = os.path.join(
        upload_folder,
        configs_subdir
    )

    # --------------------------------------------------------
    # XAVFSIZ ABSOLUTE PATH
    # --------------------------------------------------------

    configs_root = os.path.abspath(
        configs_folder
    )

    file_path = os.path.abspath(
        os.path.join(
            configs_root,
            filename
        )
    )

    # --------------------------------------------------------
    # PATH TRAVERSAL HIMOYASI
    # --------------------------------------------------------

    if not file_path.startswith(
        configs_root + os.sep
    ):

        current_app.logger.warning(
            "Noto'g'ri config path: %s",
            filename
        )

        abort(404)

    # --------------------------------------------------------
    # FAYL MAVJUDMI?
    # --------------------------------------------------------

    if not os.path.isfile(file_path):

        current_app.logger.error(
            "Config fayli topilmadi: %s",
            file_path
        )

        flash(
            "Config fayli serverda topilmadi.",
            "danger"
        )

        return redirect(
            url_for(
                "configs.config_detail",
                slug=slug
            )
        )

    # --------------------------------------------------------
    # DOWNLOAD LOG
    # --------------------------------------------------------

    download = Download(
        order_id=order.id,
        user_id=current_user.id,
        ip_address=request.remote_addr
    )

    db.session.add(download)
    db.session.commit()

    # --------------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------------

    return send_file(
        file_path,
        as_attachment=True,
        download_name=os.path.basename(file_path)
    )


# ============================================================
# REVIEW YUBORISH
# ============================================================

@configs_bp.route(
    "/config/<slug>/review",
    methods=["POST"]
)
@login_required
def submit_review(slug):

    config = Config.query.filter_by(
        slug=slug,
        is_active=True,
        is_hidden=False
    ).first_or_404()

    # --------------------------------------------------------
    # SOTIB OLGANMI?
    # --------------------------------------------------------

    if not current_user.has_purchased(
        config.id
    ):

        flash(
            "Faqat sotib olgan foydalanuvchilar review yoza oladi.",
            "danger"
        )

        return redirect(
            url_for(
                "configs.config_detail",
                slug=slug
            )
        )

    # --------------------------------------------------------
    # OLDIN REVIEW YOZGANMI?
    # --------------------------------------------------------

    existing = Review.query.filter_by(
        user_id=current_user.id,
        config_id=config.id
    ).first()

    if existing:

        flash(
            "Siz bu config uchun allaqachon review qoldirgansiz.",
            "warning"
        )

        return redirect(
            url_for(
                "configs.config_detail",
                slug=slug
            )
        )

    # --------------------------------------------------------
    # REVIEW FORM
    # --------------------------------------------------------

    form = ReviewForm()

    if form.validate_on_submit():

        review = Review(
            user_id=current_user.id,
            config_id=config.id,
            rating=form.rating.data,
            comment=form.comment.data,
        )

        db.session.add(review)
        db.session.commit()

        flash(
            "Review qo'shildi. Rahmat!",
            "success"
        )

    else:

        flash(
            "Review formasi noto'g'ri to'ldirilgan.",
            "danger"
        )

    return redirect(
        url_for(
            "configs.config_detail",
            slug=slug
        )
    )
