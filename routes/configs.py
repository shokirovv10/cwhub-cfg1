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
from app.models import Config, Category, Review
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

    # Qidiruv
    if q:
        like = f"%{q}%"

        query = query.filter(
            db.or_(
                Config.name.ilike(like),
                Config.author.ilike(like)
            )
        )

    # Kategoriya
    if category_id:
        query = query.filter_by(
            category_id=category_id
        )

    # Saralash
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

        # average_rating property bo'lsa,
        # paginationdan keyin Python orqali saralanadi.
        query = query.order_by(
            Config.created_at.desc()
        )

    else:

        # Yangi configlar
        query = query.order_by(
            Config.created_at.desc()
        )

    # Pagination
    pagination = query.paginate(
        page=page,
        per_page=PER_PAGE,
        error_out=False
    )

    items = pagination.items

    # Rating bo'yicha saralash
    if sort == "rating":

        items = sorted(
            items,
            key=lambda c: c.average_rating,
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

    config = Config.query.filter_by(
        slug=slug,
        is_active=True,
        is_hidden=False
    ).first_or_404()

    # --------------------------------------------------------
    # Sotib olganligini tekshirish
    # --------------------------------------------------------

    if not current_user.has_purchased(config.id):

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
    # Fayl yo'lini olish
    # --------------------------------------------------------

    filename = config.file_path

    if not filename:

        flash(
            "Config fayli biriktirilmagan.",
            "danger"
        )

        return redirect(
            url_for(
                "configs.config_detail",
                slug=slug
            )
        )

    # --------------------------------------------------------
    # Upload folder
    # --------------------------------------------------------

    upload_folder = current_app.config.get(
        "UPLOAD_FOLDER"
    )

    if not upload_folder:

        current_app.logger.error(
            "UPLOAD_FOLDER konfiguratsiyasi mavjud emas."
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

    # --------------------------------------------------------
    # To'liq fayl yo'li
    # --------------------------------------------------------

    file_path = os.path.abspath(
        os.path.join(
            upload_folder,
            filename
        )
    )

    upload_root = os.path.abspath(
        upload_folder
    )

    # --------------------------------------------------------
    # Security:
    # Upload papkasidan tashqariga chiqishni bloklash
    # --------------------------------------------------------

    if not file_path.startswith(
        upload_root + os.sep
    ):

        current_app.logger.warning(
            "Noto'g'ri fayl yo'liga urinish: %s",
            filename
        )

        abort(404)

    # --------------------------------------------------------
    # Fayl mavjudligini tekshirish
    # --------------------------------------------------------

    if not os.path.isfile(file_path):

        current_app.logger.error(
            "Config fayli serverda topilmadi: %s",
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
    # Download count
    # --------------------------------------------------------

    if hasattr(config, "download_count"):

        config.download_count = (
            config.download_count or 0
        ) + 1

        db.session.commit()

    # --------------------------------------------------------
    # Faylni yuklash
    # --------------------------------------------------------

    return send_file(
        file_path,
        as_attachment=True,
        download_name=os.path.basename(
            file_path
        )
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
    # Sotib olganmi?
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
    # Oldin review yozganmi?
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
    # Form
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
