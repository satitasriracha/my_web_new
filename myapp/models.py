from django.db import models
from django.db.models import F, Sum, Case, When, Value, IntegerField
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import pre_save
from datetime import datetime


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    expire_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expire_at

    def __str__(self):
        return f"Token for {self.user.username}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    
    user_code = models.CharField(max_length=10, unique=True, null=True, blank=True)  # ✅ เพิ่มตรงนี้

    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    position = models.CharField(
        max_length=20,
        choices=[("employee", "พนักงาน"), ("admin", "แอดมิน"), ("owner", "เจ้าของกิจการ")],
        default="employee",
    )

    def __str__(self):
        return f"{self.user_code} - {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    # ✅ generate หลังจากมี user.id แล้ว
        if not self.user_code:
            self.user_code = f"USR-{self.user.id:03d}"
            super().save(update_fields=["user_code"])

        super().save(*args, **kwargs)

    # ✅ sync group (ของเดิมคุณ)
        if self.position:
            group, created = Group.objects.get_or_create(name=self.position)
            self.user.groups.clear()
            self.user.groups.add(group)


# -------------------------
# ข้อมูลลูกค้า
# -------------------------
class VisibleCustomerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_hidden=False)

class Customer(models.Model):
    id = models.AutoField(primary_key=True)
    customer_id = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()

    is_special = models.BooleanField(default=False, verbose_name="ลูกค้าพิเศษ")
    is_hidden = models.BooleanField(default=False)

    password = models.CharField(
        max_length=128, blank=True, null=True, verbose_name="รหัสผ่าน"
    )

    # ✅ Managers
    objects = models.Manager()
    visible = VisibleCustomerManager()

    class Meta:
        # ✅ บังคับว่า customer_id ต้องไม่ซ้ำ ถ้า is_hidden=False
        constraints = [
            models.UniqueConstraint(
                fields=["customer_id"],
                condition=models.Q(is_hidden=False),
                name="unique_visible_customer_id",
            )
        ]

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password

        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password

        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.customer_id} - {self.name}"


# ✅ Signal: backup ข้อมูลก่อนอัพเดต
@receiver(pre_save, sender=Customer)
def backup_customer_000(sender, instance, **kwargs):
    # ทำงานเฉพาะเวลามีการอัพเดต "000" ที่ใช้งานจริง (ไม่ hidden)
    if instance.customer_id == "000" and not instance.is_hidden and instance.pk:
        try:
            old = Customer.objects.get(pk=instance.pk)
            backup = Customer.objects.filter(customer_id="000", is_hidden=True).first()
            if backup:
                backup.name = old.name
                backup.phone = old.phone
                backup.address = old.address
                backup.is_special = old.is_special
                backup.password = old.password
                backup.save()
        except Customer.DoesNotExist:
            pass


# -------------------------
# ข้อมูลพนักงาน
# -------------------------
class Employee(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="employee",
        primary_key=True,
    )
    phone = models.CharField("เบอร์โทร", max_length=20, blank=True, null=True)
    address = models.TextField("ที่อยู่", blank=True, null=True)

    def __str__(self):
        return f"Employee: {self.user.username} ({self.user.first_name} {self.user.last_name})"

    class Meta:
        verbose_name = "พนักงาน"
        verbose_name_plural = "พนักงาน"


# ==================== Product ====================
class Product(models.Model):
    CATEGORY_CHOICES = [
        ("ยูคา", "ถ่านไม้ยูคา"),
        ("โกงกาง", "ถ่านไม้โกงกาง"),
        ("เกษตร", "ถ่านไม้เกษตร"),
        ("มะขาม", "ถ่านไม้มะขาม"),
    ]

    WEIGHT_CHOICES = [
        (1.0, "1 กก."),
        (5.0, "5 กก."),
        (15.0, "15 กก."),
        (25.0, "25 กก."),
    ]

    product_id = models.CharField("รหัสสินค้า", max_length=10, primary_key=True)
    product_name = models.CharField("ชื่อสินค้า", max_length=100, default=None)
    price = models.DecimalField("ราคา", max_digits=10, decimal_places=2, default=0.00)
    quantity = models.PositiveIntegerField("จำนวน", default=0)
    weight = models.DecimalField(
        "น้ำหนัก", max_digits=5, decimal_places=1, choices=WEIGHT_CHOICES, default=1.0
    )
    image = models.ImageField(
        "รูปสินค้า", upload_to="product_images/", blank=True, null=True
    )
    # ✅ ฟิลด์ใหม่
    category = models.CharField(
        "หมวดหมู่สินค้า", max_length=20, choices=CATEGORY_CHOICES, default="ยูคา"
    )

    def __str__(self):
        return f"{self.product_id} : {self.product_name}"

    def get_weight_display(self):
        return dict(self.WEIGHT_CHOICES).get(self.weight, f"{self.weight} กก.")

    class Meta:
        verbose_name = "สินค้า"
        verbose_name_plural = "สินค้า"



# ==================== ProductReceive ====================
class ProductReceive(models.Model):
    receive_id = models.CharField(max_length=20, unique=True)
    receive_date = models.DateField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=None
    )

    def __str__(self):
        return f"{self.receive_id} ({self.receive_date})"

    def getTotalItems(self):
        return sum([it.quantity for it in self.items.all()])

    def getItemCount(self):
        return self.items.count()

    def save(self, *args, **kwargs):
        if not self.receive_id:
            today = datetime.today().strftime("%Y%m")
            prefix = f"RCV-{today}"

            last = (
                ProductReceive.objects.filter(receive_id__startswith=prefix)
                .order_by("-receive_id")
                .first()
            )

            if last:
                last_number = int(last.receive_id.split("-")[-1]) + 1
            else:
                last_number = 1

            self.receive_id = f"{prefix}-{last_number:04d}"

        super().save(*args, **kwargs)


# ==================== ProductReceiveItem ====================
class ProductReceiveItem(models.Model):
    receive = models.ForeignKey(
        ProductReceive, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=None)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.product_name} x {self.quantity}"


# -------------------------
# 6. ข้อมูลการขายสินค้า
# -------------------------
class Sale(models.Model):
    STATUS_CHOICES = [
        (0, "สั่งซื้อสินค้า"),
        (1, "แจ้งชำระเงิน"),
        (2, "ยืนยันการโอน"),
        (3, "รอการจัดส่ง"),
        (4, "จัดส่งเสร็จสิ้น"),
    ]

    sale_code = models.CharField("รหัสการขาย", max_length=20, unique=True, blank=True)
    sale_date = models.DateField("วันที่ขาย", default=timezone.now)

    employee = models.ForeignKey(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="พนักงาน",
    )
    customer = models.ForeignKey(
        "Customer", on_delete=models.CASCADE, verbose_name="ลูกค้า"
    )
    shipping_fee = models.DecimalField(
        "ค่าขนส่ง", max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    status = models.IntegerField("สถานะ", choices=STATUS_CHOICES, default=0)
    note = models.TextField("หมายเหตุ", blank=True, null=True)

    class Meta:
        verbose_name = "การขายสินค้า"
        verbose_name_plural = "การขายสินค้า"
        ordering = ["-sale_date", "-id"]

    def __str__(self):
        return f"{self.sale_code} - {self.customer.name} ({self.sale_date})"

    # ✅ รวมราคาสินค้าทั้งหมด (ไม่รวมค่าขนส่ง)
    @property
    def items_total(self):
        return sum(item.get_total() for item in self.items.all())

    # ✅ คำนวณค่าขนส่ง
    def calculate_shipping(self):
        total_weight = sum(
            (item.product.weight or 0) * (item.quantity or 0)
            for item in self.items.all()
        )
        rate = (
            ShippingRate.objects.filter(weight__gte=total_weight)
            .order_by("weight")
            .first()
        )
        if rate:
            return rate.rate
        last = ShippingRate.objects.order_by("-weight").first()
        return last.rate if last else Decimal("0.00")

    # ✅ รวมสุทธิ (สินค้า + ค่าขนส่ง)
    def get_total(self):
        return self.items_total + self.calculate_shipping()

    def save(self, *args, **kwargs):
        if not self.sale_code:
            today_str = timezone.now().strftime("%Y%m")
            prefix = f"SA-{today_str}"

            last_sale = (
                Sale.objects.filter(sale_code__startswith=prefix)
                .order_by("-id")
                .first()
            )

            if last_sale and last_sale.sale_code:
                try:
                    last_number = int(last_sale.sale_code.split("-")[-1])
                except ValueError:
                    last_number = 0
                new_number = last_number + 1
            else:
                new_number = 1
            self.sale_code = f"{prefix}-{new_number:03d}"
        super().save(*args, **kwargs)


class SaleItem(models.Model):
    sale = models.ForeignKey(
        "Sale", on_delete=models.CASCADE, related_name="items", verbose_name="รหัสการขาย"
    )
    product = models.ForeignKey(
        "Product", on_delete=models.CASCADE, verbose_name="สินค้า"
    )
    price = models.DecimalField("ราคาต่อหน่วย", max_digits=10, decimal_places=2)
    quantity = models.IntegerField("จำนวน")

    class Meta:
        verbose_name = "รายการสินค้าในใบขาย"
        verbose_name_plural = "รายการสินค้าในใบขาย"

    def __str__(self):
        return f"{self.sale.sale_code} - {self.product.product_name} ({self.quantity})"

    def get_total(self):
        return self.price * self.quantity

    # ✅ ฟิลด์เสริมให้โชว์ใน Admin
    def sale_code(self):
        return self.sale.sale_code

    sale_code.short_description = "รหัสการขาย"

    def product_info(self):
        """รหัสสินค้า + ชื่อ + น้ำหนัก"""
        return f"{self.product.product_id} {self.product.product_name} ({self.product.weight} กก.)"

    product_info.short_description = "สินค้า"

    def shipping_fee(self):
        return self.sale.shipping_fee

    shipping_fee.short_description = "ค่าขนส่ง"

    def grand_total(self):
        return self.get_total() + self.sale.shipping_fee

    grand_total.short_description = "รวมสุทธิ"


# -------------------------
# 7. ข้อมูลการชำระเงิน
# -------------------------
class Payment(models.Model):
    sale = models.OneToOneField(
        Sale, on_delete=models.CASCADE, verbose_name="รหัสการขายสินค้า", primary_key=True
    )
    pay_total = models.DecimalField(
        "ยอดชำระเงิน", max_digits=13, decimal_places=2, default=Decimal("0.00")
    )

    PAY_TYPE_CHOICES = (
        (0, "โอนเงิน"),
        (1, "จ่ายเงินปลายทาง"),
    )
    pay_type = models.IntegerField(
        "ประเภทการชำระเงิน", choices=PAY_TYPE_CHOICES, default=0
    )
    date = models.DateTimeField("วันที่ชำระเงิน", auto_now_add=True)
    slip_image = models.ImageField(
        "รูปภาพสลิป", upload_to="payment_slips/", null=True, blank=True
    )

    def __str__(self):
        return f"{self.sale} - {self.pay_total} ({self.get_pay_type_display()})"

    class Meta:
        verbose_name = "ข้อมูลการชำระเงิน"
        verbose_name_plural = "ข้อมูลการชำระเงิน"


# -------------------------
# 8. ข้อมูลการยืนยันการชำระเงิน
# -------------------------
class PaymentConfirmation(models.Model):
    confirmation_id = models.CharField(
        "รหัสใบเสร็จ", max_length=10, primary_key=True, editable=False
    )
    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, verbose_name="รหัสการขายสินค้า"
    )
    confirm_date = models.DateField("วันที่ยืนยัน", auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.confirmation_id:
            last = PaymentConfirmation.objects.order_by("-confirmation_id").first()
            if (
                last
                and last.confirmation_id.startswith("RCPT")
                and last.confirmation_id[4:].isdigit()
            ):
                last_id = int(last.confirmation_id[4:]) + 1
            else:
                last_id = 1
            self.confirmation_id = f"RCPT{last_id:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.confirmation_id

    class Meta:
        verbose_name = "การยืนยันการชำระเงิน"
        verbose_name_plural = "การยืนยันการชำระเงิน"


# -------------------------
# 9. ข้อมูลการจัดส่ง
# -------------------------
class Delivery(models.Model):
    delivery_id = models.CharField(
        "รหัสการจัดส่ง", max_length=10, primary_key=True, editable=False
    )
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="deliveries")
    delivery_date = models.DateField("วันที่จัดส่ง", auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    # ✅ เพิ่มตรงนี้
    address = models.TextField("ที่อยู่จัดส่ง", blank=True, null=True)
    status = models.CharField("สถานะ", max_length=50, default="pending")

    tracking_number = models.CharField("หมายเลขพัสดุ", max_length=100, blank=True)
    company = models.CharField("บริษัทขนส่ง", max_length=100, blank=True)

    def save(self, *args, **kwargs):
        if not self.delivery_id:
            last = Delivery.objects.order_by("-delivery_id").first()
            if (
                last
                and last.delivery_id.startswith("DLV")
                and last.delivery_id[3:].isdigit()
            ):
                last_id = int(last.delivery_id[3:]) + 1
            else:
                last_id = 1
            self.delivery_id = f"DLV{last_id:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.delivery_id} - {self.sale.pk} - {self.tracking_number}"

    class Meta:
        verbose_name = "การจัดส่ง"
        verbose_name_plural = "การจัดส่ง"


# -------------------------
# 10. ข้อมูลร้านค้า
# -------------------------
class Store(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="ชื่อร้านค้า",
    )
    number = models.CharField(
        max_length=15,
        verbose_name="เบอร์โทรศัพท์",
    )
    address = models.TextField(
        verbose_name="ที่อยู่ร้านค้า",
    )
    bank_account = models.TextField(
        verbose_name="บัญชีธนาคาร",
        blank=True,
        null=True,
    )
    general_customer = models.CharField(
        max_length=10,
        verbose_name="รหัสลูกค้าทั่วไป (สำหรับการขายหน้าร้าน)",
        default="000",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.name} ({self.general_customer})"


# -------------------------
# 11. อัตราค่าขนส่ง
# -------------------------
class ShippingRate(models.Model):
    weight = models.FloatField("น้ำหนัก (กก.)", unique=True)
    rate = models.DecimalField("อัตราค่าขนส่ง (บาท)", max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.weight} กก. : {self.rate} บาท"

    class Meta:
        verbose_name = "อัตราค่าขนส่ง"
        verbose_name_plural = "อัตราค่าขนส่ง"
        ordering = ["weight"]

# ==================== CartItem ====================
class CartItem(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):
        return self.product.price * self.quantity