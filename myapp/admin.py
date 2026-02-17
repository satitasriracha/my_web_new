from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    ProductReceive,
    ProductReceiveItem,
    Product,
    SaleItem,
    Customer,
    Sale,
    Payment,
    PaymentConfirmation,
    Delivery,
    Employee,
    Store,
    ShippingRate,
)

# -------------------------
# User (ใช้ auth.User เดิม)
# -------------------------
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ("username", "first_name", "last_name", "email", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")

    # ฟิลด์ที่จะโชว์ตอน Add user
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "email",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


# -------------------------
# Customer
# -------------------------
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "customer_id",
        "name",
        "phone",
        "address",
        "is_special",   # ✅ ใช้ is_special แทน status
    )
    search_fields = ("customer_id", "name", "phone")
    list_filter = ("is_special",)   # ✅ ลบ status ออก

    def get_username(self, obj):
        return obj.user.username if hasattr(obj, "user") and obj.user else "-"

    get_username.short_description = "ชื่อผู้ใช้"


# -------------------------
# Employee
# -------------------------
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("user", "get_full_name", "get_user_phone", "get_user_email")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )
    ordering = ("user",)
    readonly_fields = ("user",)

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    get_full_name.short_description = "ชื่อ"

    def get_user_phone(self, obj):
        # ถ้า phone อยู่ที่ Customer เท่านั้นก็ return "-"
        return getattr(obj.user, "phone", "-")

    get_user_phone.short_description = "เบอร์โทร"

    def get_user_email(self, obj):
        return obj.user.email

    get_user_email.short_description = "อีเมล"


# -------------------------
# ProductReceive & Inline
# -------------------------
class ProductReceiveItemInline(admin.TabularInline):
    model = ProductReceiveItem
    autocomplete_fields = ("product",)
    extra = 0
    min_num = 0
    fields = ("product", "quantity")
    verbose_name = "รายการสินค้า"
    verbose_name_plural = "รายการสินค้าในใบรับ"


@admin.register(ProductReceive)
class ProductReceiveAdmin(admin.ModelAdmin):
    list_display = (
        "receive_id",
        "receive_date",
        "user",
        "total_items_display",
        "total_qty_display",
    )
    search_fields = ("receive_id", "user__username", "user__first_name")
    list_filter = ("receive_date", "user")
    date_hierarchy = "receive_date"
    ordering = ("-receive_date", "-receive_id")
    inlines = [ProductReceiveItemInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _items_count=Count("items"),
            _qty_sum=Sum("items__quantity"),
        )

    def total_items_display(self, obj):
        return getattr(obj, "_items_count", 0)

    total_items_display.short_description = "จำนวนรายการ"

    def total_qty_display(self, obj):
        return getattr(obj, "_qty_sum", 0) or 0

    total_qty_display.short_description = "รวมจำนวน"


# -------------------------
# Product
# -------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("product_id", "product_name", "price", "quantity")
    search_fields = ("product_id", "product_name")


# -------------------------
# Sale
# -------------------------
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "sale_code",  # 🔄 เปลี่ยนจาก id → sale_code
        "sale_date",
        "customer_name",
        "employee_name",
        "shipping_fee",
        "status_text",
        "total_amount",
    )
    list_filter = ("sale_date", "status")
    search_fields = (
        "sale_code",
        "customer__name",
        "employee__user__first_name",
        "note",
    )  # ✅ เพิ่มค้นหาด้วยรหัสการขาย
    ordering = ("-sale_date", "-id")

    def customer_name(self, obj):
        return obj.customer.name if obj.customer else "-"

    customer_name.short_description = "ลูกค้า"

    def employee_name(self, obj):
        if obj.employee and obj.employee.user:
            return f"{obj.employee.user.first_name} {obj.employee.user.last_name}"
        return "-"

    employee_name.short_description = "พนักงาน"

    def status_text(self, obj):
        return obj.get_status_display()

    status_text.short_description = "สถานะ"

    def total_amount(self, obj):
        return obj.get_total()  # ✅ ใช้ method ที่เราแก้ใน Sale model

    total_amount.short_description = "ยอดรวม"


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = (
        "sale_code",       # รหัสการขาย
        "product_info",    # ✅ รหัสสินค้า + ชื่อ + กิโลกรัม
        "quantity",
        "price",
        "get_total",
        "shipping_fee",
        "grand_total",
    )


# -------------------------
# Payment
# -------------------------
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("sale", "pay_total", "pay_type_display", "date", "slip_preview")
    search_fields = ("sale", "pay_total")
    list_filter = ("pay_type", "date")
    readonly_fields = ("slip_preview",)

    def pay_type_display(self, obj):
        return obj.get_pay_type_display()

    pay_type_display.short_description = "ประเภทการชำระเงิน"

    def slip_preview(self, obj):
        if obj.slip_image:
            return format_html(
                '<img src="{}" style="max-height: 100px;" />', obj.slip_image.url
            )
        return "-"

    slip_preview.short_description = "รูปสลิป"


# -------------------------
# PaymentConfirmation
# -------------------------
@admin.register(PaymentConfirmation)
class PaymentConfirmationAdmin(admin.ModelAdmin):
    list_display = ("confirmation_id", "payment", "confirm_date", "user")
    search_fields = ("confirmation_id", "payment__id", "user__username")
    list_filter = ("confirm_date",)


# -------------------------
# Delivery
# -------------------------
@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "delivery_id",
        "sale",
        "delivery_date",
        "tracking_number",
        "company",
    )
    search_fields = ("delivery_id", "sale__id", "tracking_number", "company")
    list_filter = ("delivery_date", "company")


# -------------------------
# Store
# -------------------------
@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "number", "address", "bank_account", "general_customer")
    search_fields = ("name", "number", "bank_account", "general_customer")


# -------------------------
# ShippingRate
# -------------------------
@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ["weight", "rate"]
