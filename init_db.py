"""
Ma'lumotlar bazasini yaratish va boshlang'ich (seed) ma'lumotlarni kiritish.

Ishga tushirish:
    python init_db.py
"""
from app import create_app
from app.extensions import db
from app.models import User, Admin, Category, PaymentSettings, SiteSettings
from app.config import Config as AppConfig

app = create_app()

with app.app_context():
    db.create_all()
    print("[OK] Jadvallar yaratildi.")

    # --- Admin foydalanuvchi ---
    admin_user = User.query.filter_by(username=AppConfig.ADMIN_USERNAME).first()
    if not admin_user:
        admin_user = User(username=AppConfig.ADMIN_USERNAME, email=AppConfig.ADMIN_EMAIL)
        admin_user.set_password(AppConfig.ADMIN_PASSWORD)
        db.session.add(admin_user)
        db.session.flush()
        db.session.add(Admin(user_id=admin_user.id, is_super_admin=True))
        db.session.commit()
        print(f"[OK] Admin yaratildi -> username: {AppConfig.ADMIN_USERNAME}  parol: (.env dagi ADMIN_PASSWORD)")
    else:
        print("[SKIP] Admin allaqachon mavjud.")

    # --- Standart kategoriyalar ---
    default_categories = [
        ("Aim Configs", "aim-configs"),
        ("Movement Configs", "movement-configs"),
        ("HUD / Visual", "hud-visual"),
        ("Pro Player Configs", "pro-player-configs"),
        ("Sound Configs", "sound-configs"),
    ]
    for name, slug in default_categories:
        if not Category.query.filter_by(slug=slug).first():
            db.session.add(Category(name=name, slug=slug))
    db.session.commit()
    print("[OK] Standart kategoriyalar tayyor.")

    # --- Payment settings (singleton) ---
    if not PaymentSettings.query.first():
        db.session.add(PaymentSettings(
            uzcard_number=AppConfig.DEFAULT_UZCARD_NUMBER,
            humo_number=AppConfig.DEFAULT_HUMO_NUMBER,
            card_owner=AppConfig.DEFAULT_CARD_OWNER,
            payment_instructions="To'lovni amalga oshirgach, chekni saytga yuklang. Admin 24 soat ichida tekshiradi.",
            payment_api_enabled=AppConfig.PAYMENT_API_ENABLED,
        ))
        db.session.commit()
        print("[OK] To'lov sozlamalari yaratildi.")

    # --- Site settings (singleton) ---
    if not SiteSettings.query.first():
        db.session.add(SiteSettings(
            site_name="CwHUB CFG",
            telegram_url="https://t.me/",
            contact_email=AppConfig.ADMIN_EMAIL,
        ))
        db.session.commit()
        print("[OK] Sayt sozlamalari yaratildi.")

print("\nTayyor! `python run.py` bilan serverni ishga tushiring.")
