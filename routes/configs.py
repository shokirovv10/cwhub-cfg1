from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Config, Category, Review
from app.forms import ReviewForm

configs_bp = Blueprint("configs", __name__)

PER_PAGE = 9


@configs_bp.route("/configs")
def config_list():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    sort = request.args.get("sort", "newest")
    page = request.args.get("page", 1, type=int)

    query = Config.query.filter_by(is_active=True, is_hidden=False)

    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Config.name.ilike(like), Config.author.ilike(like)))

    if category_id:
        query = query.filter_by(category_id=category_id)

    if sort == "price_asc":
        query = query.order_by(Config.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Config.price.desc())
    elif sort == "bestselling":
        query = query.order_by(Config.sales_count.desc())
    elif sort == "rating":
        # rating hisoblanadigan property bo'lgani uchun python darajasida saralanadi (kichik datasetlar uchun yetarli)
        pass
    else:
        query = query.order_by(Config.created_at.desc())

    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)
    items = pagination.items
    if sort == "rating":
        items = sorted(items, key=lambda c: c.average_rating, reverse=True)

    categories = Category.query.all()
    return render_template(
        "configs.html", configs=items, pagination=pagination, categories=categories,
        q=q, category_id=category_id, sort=sort,
    )


@configs_bp.route("/config/<slug>")
def config_detail(slug):
    config = Config.query.filter_by(slug=slug, is_active=True).first_or_404()
    already_purchased = False
    can_review = False
    if current_user.is_authenticated:
        already_purchased = current_user.has_purchased(config.id)
        has_reviewed = Review.query.filter_by(user_id=current_user.id, config_id=config.id).first()
        can_review = already_purchased and not has_reviewed

    reviews = config.reviews.order_by(Review.created_at.desc()).all()
    review_form = ReviewForm()
    return render_template(
        "config_detail.html", config=config, already_purchased=already_purchased,
        reviews=reviews, can_review=can_review, review_form=review_form,
    )


@configs_bp.route("/config/<slug>/review", methods=["POST"])
@login_required
def submit_review(slug):
    config = Config.query.filter_by(slug=slug).first_or_404()

    if not current_user.has_purchased(config.id):
        flash("Faqat sotib olgan foydalanuvchilar review yoza oladi.", "danger")
        return redirect(url_for("configs.config_detail", slug=slug))

    existing = Review.query.filter_by(user_id=current_user.id, config_id=config.id).first()
    if existing:
        flash("Siz bu config uchun allaqachon review qoldirgansiz.", "warning")
        return redirect(url_for("configs.config_detail", slug=slug))

    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            user_id=current_user.id, config_id=config.id,
            rating=form.rating.data, comment=form.comment.data,
        )
        db.session.add(review)
        db.session.commit()
        flash("Review qo'shildi. Rahmat!", "success")
    else:
        flash("Review formasi noto'g'ri to'ldirilgan.", "danger")

    return redirect(url_for("configs.config_detail", slug=slug))
