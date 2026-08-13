"""
Database modellari (SQLite dev, PostgreSQLga ko'chirish uchun to'liq tayyor -
faqat DATABASE_URL ni almashtirish kifoya, SQLAlchemy ORM abstraktsiya beradi).
"""
import enum
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


def now_utc():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# ENUMS
# ---------------------------------------------------------------------------
class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    AWAITING_RECEIPT = "AWAITING_RECEIPT"
    UNDER_REVIEW = "UNDER_REVIEW"
    PAID = "PAID"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# USERS
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_filename = db.Column(db.String(255), nullable=True)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc, nullable=False)

    orders = db.relationship("Order", backref="user", lazy="dynamic", foreign_keys="Order.user_id")
    reviews = db.relationship("Review", backref="user", lazy="dynamic")
    admin_profile = db.relationship("Admin", backref="user", uselist=False)

    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self) -> bool:
        return self.admin_profile is not None

    def has_purchased(self, config_id: int) -> bool:
        return self.orders.filter_by(config_id=config_id, status=OrderStatus.PAID.value).first() is not None


class Admin(db.Model):
    """Alohida jadval - kelajakda Super Admin / role-based tizimga oson kengaytirish uchun."""
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc, nullable=False)


# ---------------------------------------------------------------------------
# CATALOG
# ---------------------------------------------------------------------------
class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    slug = db.Column(db.String(64), unique=True, nullable=False)

    configs = db.relationship("Config", backref="category", lazy="dynamic")


class Config(db.Model):
    __tablename__ = "configs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False, default="")
    features = db.Column(db.Text, nullable=True)  # newline-separated xususiyatlar ro'yxati
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    author = db.Column(db.String(80), nullable=False)
    cs_version = db.Column(db.String(40), nullable=False, default="CS 1.6")
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    screenshot_filename = db.Column(db.String(255), nullable=True)
    demo_video_url = db.Column(db.String(255), nullable=True)
    cfg_file_filename = db.Column(db.String(255), nullable=False)  # random unique nom, uploads/configs ichida

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    sales_count = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(db.DateTime, default=now_utc, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc, nullable=False)

    orders = db.relationship("Order", backref="config", lazy="dynamic")
    reviews = db.relationship("Review", backref="config", lazy="dynamic")

    @property
    def average_rating(self):
        rows = self.reviews.all()
        if not rows:
            return 0
        return round(sum(r.rating for r in rows) / len(rows), 1)

    @property
    def review_count(self):
        return self.reviews.count()


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    config_id = db.Column(db.Integer, db.ForeignKey("configs.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=now_utc, nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "config_id", name="uq_review_user_config"),)


# ---------------------------------------------------------------------------
# ORDERS / PAYMENTS
# ---------------------------------------------------------------------------
class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    config_id = db.Column(db.Integer, db.ForeignKey("configs.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(30), default=OrderStatus.PENDING_PAYMENT.value, nullable=False)
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=now_utc, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc, nullable=False)

    payment = db.relationship("Payment", backref="order", uselist=False)
    downloads = db.relationship("Download", backref="order", lazy="dynamic")


class Payment(db.Model):
    """Alohida payment abstraksiyasi - manual chek yoki kelajakdagi Click/Payme uchun umumiy."""
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), unique=True, nullable=False)
    provider = db.Column(db.String(30), default="manual", nullable=False)  # manual | click | payme
    status = db.Column(db.String(30), default=PaymentStatus.PENDING.value, nullable=False)
    provider_transaction_id = db.Column(db.String(120), nullable=True)  # kelajakdagi API uchun
    created_at = db.Column(db.DateTime, default=now_utc, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc, nullable=False)

    receipt = db.relationship("PaymentReceipt", backref="payment", uselist=False)


class PaymentReceipt(db.Model):
    __tablename__ = "payment_receipts"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)  # random unique nom, uploads/receipts ichida
    uploaded_at = db.Column(db.DateTime, default=now_utc, nullable=False)
    reviewed_by_admin_id = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)


class Download(db.Model):
    """Har bir yuklab olishni log qilish (audit uchun)."""
    __tablename__ = "downloads"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    downloaded_at = db.Column(db.DateTime, default=now_utc, nullable=False)
    ip_address = db.Column(db.String(64), nullable=True)


# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
class PaymentSettings(db.Model):
    """Bitta qatorli singleton jadval - admin panel orqali tahrirlanadi."""
    __tablename__ = "payment_settings"

    id = db.Column(db.Integer, primary_key=True)
    uzcard_number = db.Column(db.String(40), default="")
    humo_number = db.Column(db.String(40), default="")
    card_owner = db.Column(db.String(80), default="")
    payment_instructions = db.Column(db.Text, default="")

    click_enabled = db.Column(db.Boolean, default=False)
    payme_enabled = db.Column(db.Boolean, default=False)
    payment_api_enabled = db.Column(db.Boolean, default=False)

    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc)


class SiteSettings(db.Model):
    """Bitta qatorli singleton jadval - umumiy sayt sozlamalari."""
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(80), default="CwHUB CFG")
    telegram_url = db.Column(db.String(255), default="")
    contact_email = db.Column(db.String(120), default="")
    maintenance_mode = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc)
