"""
Payment service - manual (chek orqali) va kelajakdagi Click/Payme integratsiyasi
uchun umumiy interfeys. Route'lar to'g'ridan-to'g'ri Payment modeli bilan emas,
shu servis orqali ishlaydi - shunda kelajakda provider almashtirish oson bo'ladi.

Kelajakda Click/Payme ulash uchun:
    1. create_payment() ichida provider bo'yicha branch qo'shing (masalan Click API'ga so'rov).
    2. payment_callback() da providerdan kelgan webhookni qabul qiling va
       verify_payment() orqali imzoni tekshiring.
    3. .env dagi CLICK_* / PAYME_* qiymatlarni to'ldiring, PAYMENT_API_ENABLED=true qiling.
"""
from app.extensions import db
from app.models import Payment, PaymentStatus, Order, OrderStatus, PaymentReceipt, now_utc


def create_payment(order: Order, provider: str = "manual") -> Payment:
    """Order uchun yangi Payment yozuvi yaratadi (hozircha faqat manual chek oqimi)."""
    payment = Payment(order_id=order.id, provider=provider, status=PaymentStatus.PENDING.value)
    db.session.add(payment)
    order.status = OrderStatus.AWAITING_RECEIPT.value
    db.session.commit()
    return payment


def attach_receipt(payment: Payment, filename: str) -> PaymentReceipt:
    """Foydalanuvchi chek yukladi -> receipt saqlanadi, order UNDER_REVIEW ga o'tadi."""
    receipt = PaymentReceipt(payment_id=payment.id, filename=filename)
    db.session.add(receipt)
    payment.status = PaymentStatus.UNDER_REVIEW.value
    payment.order.status = OrderStatus.UNDER_REVIEW.value
    db.session.commit()
    return receipt


def approve_payment(payment: Payment, admin_id: int):
    payment.status = PaymentStatus.APPROVED.value
    payment.order.status = OrderStatus.PAID.value
    payment.order.config.sales_count = (payment.order.config.sales_count or 0) + 1
    if payment.receipt:
        payment.receipt.reviewed_by_admin_id = admin_id
        payment.receipt.reviewed_at = now_utc()
    db.session.commit()


def reject_payment(payment: Payment, admin_id: int, reason: str = ""):
    payment.status = PaymentStatus.REJECTED.value
    payment.order.status = OrderStatus.REJECTED.value
    payment.order.rejection_reason = reason
    if payment.receipt:
        payment.receipt.reviewed_by_admin_id = admin_id
        payment.receipt.reviewed_at = now_utc()
    db.session.commit()


def check_payment(order: Order) -> str:
    """Order joriy holatini qaytaradi. Kelajakda Click/Payme uchun bu yerda
    live status so'rovi (API poll) qo'shilishi mumkin."""
    return order.status


def verify_payment(payment: Payment) -> bool:
    """Kelajakdagi avtomatik providerlar uchun imzo/callback tekshiruvi.
    Hozircha manual oqimda admin o'zi tasdiqlaydi, shuning uchun bu funksiya
    faqat placeholder - haqiqiy API ulanganda to'ldiriladi."""
    return payment.status == PaymentStatus.APPROVED.value


def payment_callback(provider: str, payload: dict):
    """Kelajakda Click/Payme webhook shu yerga tushadi.
    Hozircha PAYMENT_API_ENABLED=false bo'lgani uchun ishlatilmaydi."""
    raise NotImplementedError(
        f"{provider} uchun avtomatik callback hali ulanmagan. "
        "Bu funksiya kelajakdagi real payment API integratsiyasi uchun joy tutib turibdi."
    )
