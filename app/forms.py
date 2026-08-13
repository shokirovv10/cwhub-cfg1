from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, BooleanField, TextAreaField,
    DecimalField, SelectField, IntegerField
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, NumberRange, Optional, Regexp
)


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[
        DataRequired(), Length(min=3, max=32),
        Regexp(r"^[a-zA-Z0-9_]+$", message="Username faqat harf, raqam va _ dan iborat bo'lishi mumkin."),
    ])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[
        DataRequired(), Length(min=8, message="Parol kamida 8 belgidan iborat bo'lishi kerak."),
    ])
    confirm_password = PasswordField("Confirm password", validators=[
        DataRequired(), EqualTo("password", message="Parollar mos kelmadi."),
    ])


class LoginForm(FlaskForm):
    login = StringField("Username yoki Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Joriy parol", validators=[DataRequired()])
    new_password = PasswordField("Yangi parol", validators=[DataRequired(), Length(min=8)])
    confirm_new_password = PasswordField("Yangi parolni tasdiqlang", validators=[
        DataRequired(), EqualTo("new_password", message="Parollar mos kelmadi."),
    ])


class ProfileForm(FlaskForm):
    username = StringField("Username", validators=[
        DataRequired(), Length(min=3, max=32), Regexp(r"^[a-zA-Z0-9_]+$"),
    ])
    avatar = FileField("Avatar", validators=[
        Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"], "Faqat rasm fayllari."),
    ])


class ReviewForm(FlaskForm):
    rating = IntegerField("Reyting", validators=[DataRequired(), NumberRange(min=1, max=5)])
    comment = TextAreaField("Izoh", validators=[Optional(), Length(max=1000)])


class ReceiptUploadForm(FlaskForm):
    receipt = FileField("Chek", validators=[
        DataRequired(message="Chek faylini tanlang."),
        FileAllowed(["jpg", "jpeg", "png", "pdf"], "Faqat JPG, JPEG, PNG yoki PDF."),
    ])


class ConfigForm(FlaskForm):
    name = StringField("Nomi", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Tavsif", validators=[DataRequired()])
    features = TextAreaField("Xususiyatlar (har birini yangi qatorda)", validators=[Optional()])
    price = DecimalField("Narx", validators=[DataRequired(), NumberRange(min=0)])
    category_id = SelectField("Kategoriya", coerce=int, validators=[DataRequired()])
    author = StringField("Muallif", validators=[DataRequired(), Length(max=80)])
    cs_version = StringField("CS 1.6 versiyasi", validators=[DataRequired(), Length(max=40)])
    demo_video_url = StringField("Demo video link", validators=[Optional(), Length(max=255)])
    cfg_file = FileField("CFG fayl (.cfg / .zip)", validators=[
        Optional(), FileAllowed(["cfg", "zip"], "Faqat .cfg yoki .zip."),
    ])
    screenshot = FileField("Screenshot", validators=[
        Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"], "Faqat rasm fayllari."),
    ])
    is_active = BooleanField("Faol")
    is_hidden = BooleanField("Yashirilgan")


class CategoryForm(FlaskForm):
    name = StringField("Nomi", validators=[DataRequired(), Length(max=64)])


class PaymentSettingsForm(FlaskForm):
    uzcard_number = StringField("Uzcard raqami", validators=[Optional(), Length(max=40)])
    humo_number = StringField("Humo raqami", validators=[Optional(), Length(max=40)])
    card_owner = StringField("Karta egasi", validators=[Optional(), Length(max=80)])
    payment_instructions = TextAreaField("To'lov ko'rsatmalari", validators=[Optional()])
    click_enabled = BooleanField("Click yoqilgan (kelajakda)")
    payme_enabled = BooleanField("Payme yoqilgan (kelajakda)")
    payment_api_enabled = BooleanField("Avtomatik Payment API yoqilgan")


class SiteSettingsForm(FlaskForm):
    site_name = StringField("Sayt nomi", validators=[DataRequired(), Length(max=80)])
    telegram_url = StringField("Telegram link", validators=[Optional(), Length(max=255)])
    contact_email = StringField("Contact email", validators=[Optional(), Email()])
    maintenance_mode = BooleanField("Texnik ishlar rejimi")


class RejectOrderForm(FlaskForm):
    reason = TextAreaField("Rad etish sababi", validators=[DataRequired(), Length(max=500)])
