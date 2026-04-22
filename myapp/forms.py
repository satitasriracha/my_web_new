from django import forms
from .models import (
    User,
    Customer,
    Employee,
    ProductReceive,
    ProductReceiveItem,
    Product,
    Sale,
    SaleItem,
    Payment,
    PaymentConfirmation,
    Delivery,
    Store,
    ShippingRate,
    UserProfile,
)


class UserForm(forms.ModelForm):
    password = forms.CharField(
        label="รหัสผ่าน", widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    confirm_password = forms.CharField(
        label="ยืนยันรหัสผ่าน", widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name"]

        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "กรอกชื่อ"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "กรอกนามสกุล"}),
        }
        labels = {
            "first_name": "ชื่อ",
            "last_name": "นามสกุล",
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "รหัสผ่านไม่ตรงกัน")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        # 🔥 สร้าง username อัตโนมัติ
        user.username = f"{user.first_name}_{user.last_name}".lower()

        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    POSITION_CHOICES = [
        ("employee", "พนักงาน"),
        ("admin", "แอดมิน"),
        ("owner", "เจ้าของกิจการ"),
    ]

    position = forms.ChoiceField(
        choices=POSITION_CHOICES,
        label="ตำแหน่ง",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = UserProfile
        fields = ["address", "phone", "position"]

        widgets = {
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "address": "ที่อยู่",
            "phone": "เบอร์โทร",
            "position": "ตำแหน่ง",
        }


class ForgotPasswordForm(forms.Form):
    username = forms.CharField(
        label="Username", widget=forms.TextInput(attrs={"class": "form-control"})
    )


class ResetPasswordForm(forms.Form):
    password = forms.CharField(
        label="รหัสผ่านใหม่", widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    password2 = forms.CharField(
        label="ยืนยันรหัสผ่านใหม่",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password2"):
            raise forms.ValidationError("รหัสผ่านไม่ตรงกัน")
        return cleaned


class CustomerForm(forms.ModelForm):
    # password และ confirm_password ไม่บังคับ
    password = forms.CharField(
        label="รหัสผ่าน",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
    )
    confirm_password = forms.CharField(
        label="ยืนยันรหัสผ่าน",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
    )

    class Meta:
        model = Customer
        fields = [
            "customer_id",
            "name",
            "phone",
            "address",
            "is_special",
        ]  # ✅ แทนที่ status
        widgets = {
            "customer_id": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "is_special": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),  # ✅ checkbox
        }
        labels = {
            "customer_id": "รหัสลูกค้า",
            "name": "ชื่อ-สกุล",
            "phone": "เบอร์โทร",
            "address": "ที่อยู่",
            "is_special": "ลูกค้าพิเศษ?",  # ✅ แทนที่ status
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        # ถ้ามีการกรอก password ให้ตรวจสอบตรงกัน
        if password or confirm_password:
            if password != confirm_password:
                self.add_error("confirm_password", "รหัสผ่านไม่ตรงกัน")
        return cleaned_data

    def save(self, commit=True):
        customer = super().save(commit=False)
        password = self.cleaned_data.get("password")

        # ✅ ถ้ามีการกรอกรหัสผ่าน -> hash ก่อนบันทึก
        if password:
            customer.set_password(password)

        if commit:
            customer.save()
        return customer


class EmployeeForm(forms.ModelForm):
    first_name = forms.CharField(
        label="ชื่อ",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="นามสกุล",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Employee
        fields = ["phone", "address"]  # ✅ เอา status ออก
        widgets = {
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
        labels = {
            "phone": "เบอร์โทร",
            "address": "ที่อยู่",
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "product_id",
            "product_name",
            "price",
            "weight",
            "image",
        ]  # ไม่ใส่ quantity
        widgets = {
            "product_id": forms.TextInput(attrs={"class": "form-control"}),
            "product_name": forms.TextInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "1"}),
            "weight": forms.Select(
                choices=Product.WEIGHT_CHOICES, attrs={"class": "form-control"}
            ),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
        labels = {
            "product_id": "รหัสสินค้า",
            "product_name": "ชื่อสินค้า",
            "price": "ราคา",
            "weight": "น้ำหนัก",
            "image": "รูปสินค้า",
        }

    def clean_product_id(self):
        product_id = self.cleaned_data.get("product_id")
        if Product.objects.filter(product_id=product_id).exists():
            raise forms.ValidationError("รหัสสินค้านี้ถูกใช้งานแล้ว")
        return product_id


class ProductReceiveForm(forms.ModelForm):
    class Meta:
        model = ProductReceive
        # ใช้เฉพาะฟิลด์ที่ผู้ใช้ต้องกรอกเอง
        fields = ["user"]

        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
        }

        labels = {
            "user": "รหัสผู้ใช้ระบบ",
        }

    # แสดง receive_id และ receive_date แบบ readonly ในฟอร์ม ถ้าเป็นการแก้ไข
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["receive_id"] = forms.CharField(
                label="รหัสการรับสินค้า",
                initial=self.instance.receive_id,
                widget=forms.TextInput(
                    attrs={"class": "form-control", "readonly": True}
                ),
                required=False,
            )

            self.fields["receive_date"] = forms.DateField(
                label="วันที่รับสินค้า",
                initial=self.instance.receive_date,
                widget=forms.DateInput(
                    attrs={"class": "form-control", "type": "date", "readonly": True}
                ),
                required=False,
            )


class ProductReceiveItemForm(forms.ModelForm):
    class Meta:
        model = ProductReceiveItem
        fields = ["receive", "product", "quantity"]

        widgets = {
            "receive": forms.Select(attrs={"class": "form-control"}),
            "product": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
        }

        labels = {
            "receive": "รหัสการรับสินค้า",
            "product": "รหัสสินค้า",
            "quantity": "จำนวน",
        }


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = [
            "sale_code",
            "sale_date",
            "employee",
            "customer",
            "shipping_fee",
            "status",
            "note",
        ]
        widgets = {
            "sale_code": forms.TextInput(
                attrs={"class": "form-control", "readonly": True}
            ),
            "sale_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "employee": forms.Select(attrs={"class": "form-control"}),
            "customer": forms.Select(attrs={"class": "form-control"}),
            "shipping_fee": forms.NumberInput(attrs={"class": "form-control"}),
            "status": forms.Select(
                attrs={"class": "form-control"},
                choices=[
                    (0, "สั่งซื้อสินค้า"),
                    (1, "แจ้งชำระเงิน"),
                    (2, "ยืนยันการชำระเงิน"),
                    (3, "รอการจัดส่ง"),
                    (4, "จัดส่งเสร็จสิ้น"),
                ],
            ),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
        labels = {
            "sale_code": "รหัสการขาย",
            "sale_date": "วันที่ขาย",
            "employee": "พนักงาน",
            "customer": "ลูกค้า",
            "shipping_fee": "ค่าขนส่ง",
            "status": "สถานะ",
            "note": "หมายเหตุ",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Customer
        self.fields["customer"].queryset = Customer.visible.all()



class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = "__all__"
        widgets = {
            "sale": forms.Select(attrs={"class": "form-control"}),
            "product": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
        }
        labels = {
            "sale": "การขาย",
            "product": "สินค้า",
            "quantity": "จำนวน",
            "price": "ราคา",
        }


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = "__all__"
        widgets = {
            "sale": forms.Select(attrs={"class": "form-control"}),
            "pay_total": forms.NumberInput(attrs={"class": "form-control"}),
            "pay_type": forms.Select(attrs={"class": "form-control"}),
            "date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "slip_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
        labels = {
            "sale": "รหัสตารางการขาย",
            "pay_total": "ยอดชำระเงิน",
            "pay_type": "ประเภทการชำระเงิน",
            "date": "วันที่ชำระเงิน",
            "slip_image": "รูปภาพสลิป",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # กรองเฉพาะ Sale ที่ยังไม่มี Payment เท่านั้น
        if not self.instance.pk:
            self.fields["sale"].queryset = Sale.objects.filter(payment__isnull=True)


class PaymentConfirmationForm(forms.ModelForm):
    class Meta:
        model = PaymentConfirmation
        fields = "__all__"
        widgets = {
            "confirmation_id": forms.TextInput(
                attrs={"class": "form-control", "readonly": True}
            ),
            "payment": forms.Select(attrs={"class": "form-control"}),
            "confirm_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "user": forms.Select(attrs={"class": "form-control"}),
        }
        labels = {
            "confirmation_id": "รหัสใบเสร็จ",
            "payment": "การชำระเงิน",
            "confirm_date": "วันที่ยืนยัน",
            "user": "ผู้ยืนยัน",
        }


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = "__all__"
        widgets = {
            "delivery_id": forms.TextInput(
                attrs={"class": "form-control", "readonly": True}
            ),
            "sale": forms.Select(attrs={"class": "form-control"}),
            "delivery_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "user": forms.Select(attrs={"class": "form-control"}),
            "tracking_number": forms.TextInput(attrs={"class": "form-control"}),
            "company": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "delivery_id": "รหัสจัดส่ง",
            "sale": "การขายสินค้า",
            "delivery_date": "วันที่จัดส่ง",
            "user": "ผู้จัดส่ง",
            "tracking_number": "เลขพัสดุ",
            "company": "บริษัทขนส่ง",
        }

class StoreForm(forms.ModelForm):
    bank_name = forms.CharField(label="ธนาคาร", required=False)
    bank_number = forms.CharField(label="เลขบัญชี", required=False)
    bank_owner = forms.CharField(label="ชื่อบัญชี", required=False)

    class Meta:
        model = Store
        fields = ["name", "address", "number", "bank_name", "bank_number", "bank_owner", "general_customer"]
        labels = {
            "name": "ชื่อร้านค้า",
            "address": "ที่อยู่ร้านค้า",
            "number": "เบอร์โทรศัพท์",
            "general_customer": "รหัสลูกค้าทั่วไป (สำหรับการขายหน้าร้าน)",
        }
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "general_customer": forms.TextInput(attrs={"placeholder": "000"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # แยก bank_account
        if self.instance and self.instance.bank_account:
            parts = self.instance.bank_account.split("|")
            if len(parts) == 3:
                self.fields["bank_name"].initial = parts[0]
                self.fields["bank_number"].initial = parts[1]
                self.fields["bank_owner"].initial = parts[2]

    def save(self, commit=True):
        instance = super().save(commit=False)

        # รวม bank_account
        name = self.cleaned_data.get("bank_name", "")
        number = self.cleaned_data.get("bank_number", "")
        owner = self.cleaned_data.get("bank_owner", "")
        instance.bank_account = f"{name}|{number}|{owner}"

        # ✅ อัปเดตตาราง Customer ด้วย
        new_code = self.cleaned_data.get("general_customer")
        from myapp.models import Customer
        customer = Customer.objects.filter(is_hidden=False, customer_id="000").first()
        if customer:
            customer.customer_id = new_code
            customer.save(update_fields=["customer_id"])

        if commit:
            instance.save()
        return instance


class ShippingRateForm(forms.ModelForm):
    class Meta:
        model = ShippingRate
        fields = ["weight", "rate"]
        widgets = {
            "weight": forms.NumberInput(attrs={"class": "form-control"}),
            "rate": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        weight = cleaned_data.get("weight")
        rate = cleaned_data.get("rate")

        if not weight or not rate:
            return cleaned_data

        # 🚨 ตรวจว่าน้ำหนักซ้ำ
        if (
            ShippingRate.objects.filter(weight=weight)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("❌ ไม่สามารถเพิ่มน้ำหนักกิโลกรัมนี้ได้ (มีอยู่แล้วในระบบ)")

        # 🚨 ตรวจความสัมพันธ์ของราคา
        smaller = (
            ShippingRate.objects.filter(weight__lt=weight).order_by("-weight").first()
        )
        bigger = (
            ShippingRate.objects.filter(weight__gt=weight).order_by("weight").first()
        )

        if smaller and rate < smaller.rate:
            raise forms.ValidationError(
                "❌ ไม่สามารถเพิ่มอัตราค่าขนส่งได้ (อัตราค่าส่งน้อยกว่าน้ำหนักที่น้อยกว่า)"
            )

        if bigger and rate > bigger.rate:
            raise forms.ValidationError(
                "❌ ไม่สามารถเพิ่มอัตราค่าขนส่งได้ (อัตราค่าส่งมากกว่าน้ำหนักที่มากกว่า)"
            )

        return cleaned_data
