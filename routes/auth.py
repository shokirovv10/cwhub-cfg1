from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_

from app.extensions import db, limiter
from app.models import User
from app.forms import RegisterForm, LoginForm, ProfileForm, ChangePasswordForm
from services.file_service import save_uploaded_file

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        username_taken = User.query.filter_by(username=form.username.data).first()
        email_taken = User.query.filter_by(email=form.email.data.lower()).first()

        if username_taken:
            flash("Bu username allaqachon band.", "danger")
        elif email_taken:
            flash("Bu email allaqachon ro'yxatdan o'tgan.", "danger")
        else:
            user = User(username=form.username.data, email=form.email.data.lower())
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Ro'yxatdan muvaffaqiyatli o'tdingiz!", "success")
            return redirect(url_for("main.index"))

    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("15 per hour")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.login.data.strip()
        user = User.query.filter(
            or_(User.username == identifier, User.email == identifier.lower())
        ).first()

        if user is None or not user.check_password(form.password.data):
            flash("Username/Email yoki parol noto'g'ri.", "danger")
        elif user.is_blocked:
            flash("Sizning akkountingiz bloklangan. Admin bilan bog'laning.", "danger")
        else:
            login_user(user, remember=form.remember_me.data)
            flash("Xush kelibsiz!", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("main.index"))

    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Tizimdan chiqdingiz.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        if form.username.data != current_user.username:
            exists = User.query.filter_by(username=form.username.data).first()
            if exists:
                flash("Bu username allaqachon band.", "danger")
                return render_template("profile.html", form=form, pw_form=ChangePasswordForm())
            current_user.username = form.username.data

        if form.avatar.data:
            try:
                filename = save_uploaded_file(
                    form.avatar.data, "avatars",
                    {"jpg", "jpeg", "png", "webp"}, {"image/jpeg", "image/png", "image/webp"},
                )
                current_user.avatar_filename = filename
            except ValueError as e:
                flash(str(e), "danger")
                return render_template("profile.html", form=form, pw_form=ChangePasswordForm())

        db.session.commit()
        flash("Profil yangilandi.", "success")
        return redirect(url_for("auth.profile"))

    pw_form = ChangePasswordForm()
    purchases_count = current_user.orders.filter_by(status="PAID").count()
    return render_template("profile.html", form=form, pw_form=pw_form, purchases_count=purchases_count)


@auth_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    pw_form = ChangePasswordForm()
    if pw_form.validate_on_submit():
        if not current_user.check_password(pw_form.current_password.data):
            flash("Joriy parol noto'g'ri.", "danger")
        else:
            current_user.set_password(pw_form.new_password.data)
            db.session.commit()
            flash("Parol muvaffaqiyatli o'zgartirildi.", "success")
    else:
        flash("Parolni tekshiring va qayta urinib ko'ring.", "danger")
    return redirect(url_for("auth.profile"))
