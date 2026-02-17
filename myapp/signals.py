from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Sale, Payment, PaymentConfirmation, Delivery
from myapp.models import Store, Customer


@receiver(post_save, sender=Store)
def sync_general_customer(sender, instance, **kwargs):
    """
    เวลามีการ save() Store → อัปเดต Customer.customer_id ให้ตรงกับ Store.general_customer
    """
    new_code = instance.general_customer

    # ดึงลูกค้าทั่วไปตัวจริง (ไม่ hidden) — ไม่ fix ว่าต้องเป็น "000"
    customer = Customer.objects.filter(is_hidden=False, name="ลูกค้าทั่วไป").first()

    if customer:
        # อัปเดต customer_id ให้ตรงกับ Store.general_customer
        if customer.customer_id != new_code:
            customer.customer_id = new_code
            customer.save(update_fields=["customer_id"])
            
# เมื่อลูกค้าแจ้งชำระเงิน (สร้าง Payment)
@receiver(post_save, sender=Payment)
def update_status_after_payment(sender, instance, created, **kwargs):
    if created:
        sale = instance.sale
        if sale.status == 1:  # กรณีรอแจ้งชำระเงิน
            sale.status = 2  # รอการยืนยันชำระเงิน
            sale.save()


# เมื่อตรวจสอบยืนยันการชำระเงิน (สร้าง PaymentConfirmation)
@receiver(post_save, sender=PaymentConfirmation)
def update_status_after_payment_confirmation(sender, instance, created, **kwargs):
    if created:
        sale = instance.payment.sale
        if sale.status == 2:  # รอการยืนยันชำระเงิน
            sale.status = 3  # รอการจัดส่ง
            sale.save()


# เมื่อตรวจสอบจัดส่ง (สร้าง Delivery)
@receiver(post_save, sender=Delivery)
def update_status_after_delivery(sender, instance, created, **kwargs):
    if created:
        sale = instance.sale
        if sale.status == 3:  # รอการจัดส่ง
            sale.status = 4  # จัดส่งสินค้าเสร็จสิ้น
            sale.save()
