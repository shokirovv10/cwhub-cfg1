"""
CwHUB CFG - Payment Service

Manual payment:
    PENDING
        ↓
    UNDER_REVIEW
        ↓
    APPROVED / REJECTED

Order:
    PENDING_PAYMENT
        ↓
    AWAITING_RECEIPT
        ↓
    UNDER_REVIEW
        ↓
    PAID / REJECTED
"""

from app.extensions import db
from app.models import (
    Payment,
    PaymentStatus,
    Order,
    OrderStatus,
    PaymentReceipt,
    now_utc,
)


# ============================================================
# CREATE PAYMENT
# ============================================================

def create_payment(
    order: Order,
    provider: str = "manual",
) -> Payment:

    # Agar payment allaqachon mavjud bo'lsa
    if order.payment:

        payment = order.payment

        # Agar oldingi order rejected bo'lgan bo'lsa,
        # qayta to'lov boshlashga ruxsat beramiz.
        if order.status == OrderStatus.REJECTED.value:

            payment.status = PaymentStatus.PENDING.value
            order.status = OrderStatus.AWAITING_RECEIPT.value
            order.rejection_reason = None

            db.session.commit()

        return payment

    payment = Payment(
        order_id=order.id,
        provider=provider,
        status=PaymentStatus.PENDING.value,
    )

    db.session.add(payment)

    order.status = OrderStatus.AWAITING_RECEIPT.value

    db.session.commit()

    return payment


# ============================================================
# ATTACH RECEIPT
# ============================================================

def attach_receipt(
    payment: Payment,
    filename: str,
) -> PaymentReceipt:

    if not payment:
        raise ValueError("Payment topilmadi.")

    if not filename:
        raise ValueError("Receipt filename bo'sh.")

    # Eski receipt bo'lsa o'chiramiz
    old_receipt = payment.receipt

    if old_receipt:

        db.session.delete(old_receipt)
        db.session.flush()

    receipt = PaymentReceipt(
        payment_id=payment.id,
        filename=filename,
    )

    db.session.add(receipt)

    payment.status = (
        PaymentStatus.UNDER_REVIEW.value
    )

    payment.order.status = (
        OrderStatus.UNDER_REVIEW.value
    )

    payment.order.rejection_reason = None

    db.session.commit()

    return receipt


# ============================================================
# APPROVE PAYMENT
# ============================================================

def approve_payment(
    payment: Payment,
    admin_id: int,
):

    if not payment:
        raise ValueError("Payment topilmadi.")

    order = payment.order

    if not order:
        raise ValueError("Order topilmadi.")

    # Faqat UNDER_REVIEW payment tasdiqlansin
    if payment.status != PaymentStatus.UNDER_REVIEW.value:

        raise ValueError(
            "Faqat tekshirilayotgan to'lovni tasdiqlash mumkin."
        )

    # Agar receipt bo'lmasa
    if not payment.receipt:

        raise ValueError(
            "Bu payment uchun chek mavjud emas."
        )

    # Payment
    payment.status = (
        PaymentStatus.APPROVED.value
    )

    # Order
    order.status = (
        OrderStatus.PAID.value
    )

    order.rejection_reason = None

    # Receipt review
    payment.receipt.reviewed_by_admin_id = admin_id
    payment.receipt.reviewed_at = now_utc()

    # Sales count
    if order.config:

        order.config.sales_count = (
            order.config.sales_count or 0
        ) + 1

    db.session.commit()


# ============================================================
# REJECT PAYMENT
# ============================================================

def reject_payment(
    payment: Payment,
    admin_id: int,
    reason: str = "",
):

    if not payment:
        raise ValueError("Payment topilmadi.")

    order = payment.order

    if not order:
        raise ValueError("Order topilmadi.")

    if payment.status != PaymentStatus.UNDER_REVIEW.value:

        raise ValueError(
            "Faqat tekshirilayotgan to'lovni rad etish mumkin."
        )

    payment.status = (
        PaymentStatus.REJECTED.value
    )

    order.status = (
        OrderStatus.REJECTED.value
    )

    order.rejection_reason = (
        reason.strip()
        if reason
        else "To'lov tasdiqlanmadi."
    )

    if payment.receipt:

        payment.receipt.reviewed_by_admin_id = (
            admin_id
        )

        payment.receipt.reviewed_at = (
            now_utc()
        )

    db.session.commit()


# ============================================================
# RESUBMIT PAYMENT
# ============================================================

def resubmit_payment(
    payment: Payment,
):

    if not payment:
        raise ValueError("Payment topilmadi.")

    order = payment.order

    if not order:
        raise ValueError("Order topilmadi.")

    if payment.status != PaymentStatus.REJECTED.value:

        raise ValueError(
            "Faqat rad etilgan paymentni qayta yuborish mumkin."
        )

    payment.status = (
        PaymentStatus.PENDING.value
    )

    order.status = (
        OrderStatus.AWAITING_RECEIPT.value
    )

    order.rejection_reason = None

    db.session.commit()


# ============================================================
# CHECK PAYMENT
# ============================================================

def check_payment(order: Order) -> str:

    if not order:
        raise ValueError("Order topilmadi.")

    return order.status


# ============================================================
# VERIFY PAYMENT
# ============================================================

def verify_payment(payment: Payment) -> bool:

    if not payment:
        return False

    return (
        payment.status
        == PaymentStatus.APPROVED.value
    )


# ============================================================
# PAYMENT CALLBACK
# ============================================================

def payment_callback(
    provider: str,
    payload: dict,
):

    raise NotImplementedError(
        f"{provider} uchun avtomatik callback "
        "hali ulanmagan."
    )
