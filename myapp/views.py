

import json, secrets,re
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.db.models import Q, Prefetch, Sum, F, Max
from django.db import transaction
from django.utils.dateparse import parse_date
from django.contrib.auth.hashers import make_password
from django.core.serializers.json import DjangoJSONEncoder
from collections import defaultdict, OrderedDict
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from functools import wraps
from .models import (
    User,
    PasswordResetToken,
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
    UserProfile,
    CartItem
)
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.db.models import Q, Prefetch, Sum, F, Max, Count
from django.db.models.functions import TruncDate
from django.shortcuts import render, redirect
from .models import Delivery, Sale
from django.views.decorators.http import require_POST
from .forms import (
    UserForm,
    ProductReceiveForm,
    ProductReceiveItemForm,
    ProductForm,
    SaleItemForm,
    CustomerForm,
    SaleForm,
    PaymentForm,
    PaymentConfirmationForm,
    DeliveryForm,
    EmployeeForm,
    ForgotPasswordForm,
    ResetPasswordForm,
    StoreForm,
    ShippingRateForm,
    UserProfileForm,
)


User = get_user_model()


# -------------------------------
# Home / Auth
# -------------------------------
def home(request):
    user_name = None

    if request.user.is_authenticated:
        user_name = request.user.get_full_name()   # ✅ เอาแค่นี้พอ
    elif request.session.get("customer_id"):
        user_name = request.session.get("customer_name")

    products = Product.objects.all()

    return render(request, "myapp/home.html", {
        "user_name": user_name,
        "products": products
    })

# -------------------- แสดงสินค้า --------------------
def products(request):
    uka_list = Product.objects.filter(category="ยูคา").order_by("product_id")
    koukang_list = Product.objects.filter(category="โกงกาง").order_by("product_id")
    kaset_list = Product.objects.filter(category="เกษตร").order_by("product_id")
    makam_list = Product.objects.filter(category="มะขาม").order_by("product_id")

    return render(request, "products.html", {
        "uka_list": uka_list,
        "koukang_list": koukang_list,
        "kaset_list": kaset_list,
        "makam_list": makam_list,
    })



# -------------------- แสดงตะกร้า --------------------
def cart_view(request):

    # 🔥 key cart
    if request.user.is_authenticated:
        cart_key = f"cart_user_{request.user.id}"
    elif request.session.get("customer_id"):
        cart_key = f"cart_customer_{request.session.get('customer_id')}"
    else:
        cart_key = "cart_guest"

    cart = request.session.get(cart_key, {})

    items = []
    total = 0
    total_weight = 0
    total_items = 0   # 🔥 เพิ่มตัวนี้

    for pk, qty in cart.items():
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            continue

        subtotal = product.price * qty

        total += subtotal
        total_weight += (product.weight or 0) * qty
        total_items += qty   # 🔥 รวมจำนวนสินค้า

        items.append({
            "id": product.pk,
            "name": product.product_name,
            "price": float(product.price),
            "qty": qty,
            "image": product.image.url if product.image else "/static/images/noimage.jpg",
            "subtotal": float(subtotal),
            "weight": float(product.weight or 0),
        })

    # 🚚 ค่าขนส่ง
    # 🚚 ค่าขนส่ง
    shipping_fee = 0
    shipping_rates_qs = ShippingRate.objects.all().order_by("weight")

    for rate in shipping_rates_qs:
        if total_weight <= rate.weight:
            shipping_fee = rate.rate
            break

    if shipping_fee == 0 and shipping_rates_qs.exists():
        shipping_fee = shipping_rates_qs.last().rate

    # ✅ FIX ต้องมีบรรทัดนี้
    grand_total = total + shipping_fee

    shipping_rates = json.dumps(
         list(shipping_rates_qs.values("weight", "rate")),
    cls=DjangoJSONEncoder,
)

    context = {
        "items": items,
        "total": float(total),
        "total_weight": float(total_weight),
        "shipping_fee": float(shipping_fee),
        "grand_total": float(grand_total),
        "shipping_rates": shipping_rates,
        "total_items": total_items,  # 🔥 เพิ่มตรงนี้
    }

    # 🔥 AJAX
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(context)

    return render(request, "cart.html", context)
def update_sale_status(request, pk):
    if request.method == "POST":
        data = json.loads(request.body)
        sale = Sale.objects.get(pk=pk)
        sale.status = data.get("status")
        sale.save()
        return JsonResponse({"success": True})
def delivery_tracking(request):
    sale_id = request.GET.get("sale_id")

    sales = Sale.objects.select_related("customer").order_by("-id")[:50]
    sale = None

    if sale_id:
        sale = Sale.objects.filter(id=sale_id).first()

    return render(request, "myapp/delivery_tracking.html", {
        "sales": sales,
        "sale": sale
    })



@require_POST
def delivery_create(request):
    sale_id = request.POST.get("sale_id")
    address = request.POST.get("address")
    status = request.POST.get("status")

    sale = Sale.objects.get(id=sale_id)

    # 🔥 map status delivery → sale
    if status == "pending":
        sale.status = 2   # ยืนยันการโอน
    elif status == "shipping":
        sale.status = 3   # รอจัดส่ง
    elif status == "success":
        sale.status = 4   # ส่งสำเร็จ

    sale.save()

    Delivery.objects.create(
        sale=sale,
        user=request.user,
        address=address
    )

    return redirect("myapp:delivery_list")
@csrf_exempt
def update_status(request, id):
    if request.method == "POST":
        data = json.loads(request.body)
        status = int(data.get("status"))

        sale = Sale.objects.get(id=id)
        sale.status = status
        sale.save()

        return JsonResponse({
            "success": True,
            "status": sale.get_status_display()
        })
# -------------------- เพิ่มสินค้าเข้าตะกร้า --------------------
def add_to_cart(request, pk):

    # 🔥 อนุญาตเฉพาะ POST
    if request.method != "POST":
        return redirect("myapp:products")

    # 🔥 แยก cart ตาม user
    if request.user.is_authenticated:
        cart_key = f"cart_user_{request.user.id}"
    elif request.session.get("customer_id"):
        cart_key = f"cart_customer_{request.session.get('customer_id')}"
    else:
        cart_key = "cart_guest"

    cart = request.session.get(cart_key, {})

    # 🔥 เพิ่มสินค้า
    cart[str(pk)] = cart.get(str(pk), 0) + 1

    request.session[cart_key] = cart
    request.session.modified = True

    total_items = sum(cart.values())

    # 🔥 ถ้าเป็น AJAX → return JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "total_items": total_items
        })

    # 🔥 fallback → redirect ปกติ
    next_url = request.GET.get("next", "myapp:products")
    return redirect(next_url)

@login_required(login_url='login')
def checkout(request):
    # logic เดิม
    return render(request, 'checkout.html')
# -------------------- ลบสินค้าออกจากตะกร้า --------------------
def remove_from_cart(request, pk):
    """ลบสินค้าออกจากตะกร้า (ใช้ session)"""

    # 🔥 ใช้ cart_key ให้ตรงระบบ
    if request.user.is_authenticated:
        cart_key = f"cart_user_{request.user.id}"
    elif request.session.get("customer_id"):
        cart_key = f"cart_customer_{request.session.get('customer_id')}"
    else:
        cart_key = "cart_guest"

    cart = request.session.get(cart_key, {})
    success = False

    if str(pk) in cart:
        del cart[str(pk)]
        request.session[cart_key] = cart
        request.session.modified = True
        success = True

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": success, "cart": cart})

    if success:
        messages.success(request, "ลบสินค้าออกจากตะกร้าแล้ว ❌")
    else:
        messages.warning(request, "ไม่พบสินค้านี้ในตะกร้า")

    return redirect("myapp:cart")

# -------------------- อัปเดตจำนวนสินค้า --------------------

@csrf_exempt
def update_cart(request, pk):
    """อัปเดตจำนวนสินค้าในตะกร้า"""

    if request.method == "POST":

        # 🔥 ใช้ cart_key
        if request.user.is_authenticated:
            cart_key = f"cart_user_{request.user.id}"
        elif request.session.get("customer_id"):
            cart_key = f"cart_customer_{request.session.get('customer_id')}"
        else:
            cart_key = "cart_guest"

        cart = request.session.get(cart_key, {})

        try:
            data = json.loads(request.body)
        except:
            data = {}

        qty = int(data.get("qty", 1))

        if qty <= 0:
            cart.pop(str(pk), None)
        else:
            cart[str(pk)] = qty

        request.session[cart_key] = cart
        request.session.modified = True

        return JsonResponse({"success": True, "cart": cart})

    return JsonResponse({"success": False})


def generate_customer_id():
    # ดึงเฉพาะลูกค้าปกติ (is_special=False)
    last_customer = (
        Customer.objects.filter(is_special=False, customer_id__startswith="CUS-")
        .order_by("-customer_id")
        .first()
    )

    if last_customer:
        match = re.search(r"CUS-(\d+)", last_customer.customer_id)
        if match:
            last_num = int(match.group(1))
            new_id = f"CUS-{last_num+1:04d}"
        else:
            new_id = "CUS-0001"
    else:
        new_id = "CUS-0001"

    return new_id


def register(request):
    if request.method == "POST":
        name = request.POST.get("name")
        address = request.POST.get("address")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        telephone = request.POST.get("telephone")

        if password != confirm_password:
            return render(request, "myapp/register.html", {"error": "รหัสผ่านไม่ตรงกัน"})

        with transaction.atomic():
            new_customer_id = generate_customer_id()

            # ✅ เก็บ password แบบ hash
            customer = Customer(
                customer_id=new_customer_id,
                name=name,
                phone=telephone,
                address=address,
                is_special=False,
            )
            customer.set_password(password)   # 🔐 ใช้ hash
            customer.save()

        messages.success(request, "สมัครสมาชิกเรียบร้อยแล้ว ✅")
        return redirect("myapp:login")

    return render(request, "myapp/register.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # ======================
        # 🔐 Django User
        # ======================
        user = None
        # 👉 ถ้าพิมพ์เป็น USR-xxx
        if username.startswith("USR-"):
            try:
                user_id = int(username.split("-")[1]) 
                user = User.objects.filter(id=user_id).first()
            except:
                user = None
        else:
            user = authenticate(request, username=username, password=password)

        if user and user.check_password(password):
            login(request, user)        

            # 👑 แยก role
            if user.is_superuser:
               return redirect("myapp:home")

            if hasattr(user, "profile"):
                if user.profile.position == "employee":
                    return redirect("myapp:sale_list")

                elif user.profile.position == "owner":
                    return redirect("myapp:user_list")

            return redirect("myapp:home")

        # ======================
        # 👤 Customer
        # ======================
        customer = Customer.objects.filter(
            Q(name=username) | Q(phone=username)
        ).first()

        if customer:
            if customer.check_password(password):
                request.session["customer_id"] = customer.customer_id
                request.session["customer_name"] = customer.name

                return redirect("myapp:home")  # 🔥 สำคัญมาก

            else:
                return render(request, "myapp/login.html", {
                    "status": "incorrect_password"
                })

        return render(request, "myapp/login.html", {
            "status": "username_not_found"
        })

    return render(request, "myapp/login.html")




def get_current_customer(request):
    if request.session.get("customer_id"):
        return Customer.objects.filter(
            customer_id=request.session.get("customer_id")
        ).first()
    return None
def customer_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.session.get("customer_id"):
            return view_func(request, *args, **kwargs)
        return redirect("myapp:login")
    return wrapper


def employee_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, "profile"):
            if request.user.profile.position in ["employee", "owner"]:
                return view_func(request, *args, **kwargs)
        return redirect("myapp:home")
    return wrapper

def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("myapp:home")


def forgot_password_view(request):
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                form.add_error("username", "ไม่พบบัญชีผู้ใช้")
            else:
                token = secrets.token_urlsafe(20)
                expire_at = timezone.now() + timedelta(hours=1)
                PasswordResetToken.objects.create(
                    user=user, token=token, expire_at=expire_at
                )
                reset_url = request.build_absolute_uri(
                    reverse("myapp:reset_password", args=[token])
                )
                messages.success(request, f"ลิงก์รีเซ็ตถูกสร้างแล้ว: {reset_url}")
                return redirect("myapp:login")
    else:
        form = ForgotPasswordForm()
    return render(request, "myapp/forgot_password.html", {"form": form})


def reset_password_view(request, token):
    try:
        obj = PasswordResetToken.objects.get(token=token, expire_at__gte=timezone.now())
        user = obj.user
    except PasswordResetToken.DoesNotExist:
        return HttpResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status=400)

    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_pass = form.cleaned_data["password"]
            user.set_password(new_pass)
            user.save()
            obj.delete()
            messages.success(request, "รีเซ็ตรหัสผ่านเรียบร้อย กรุณาล็อกอินอีกครั้ง")
            return redirect("myapp:login")
    else:
        form = ResetPasswordForm()
    return render(request, "myapp/reset_password.html", {"form": form})


# -------------------------------
# Users
# -------------------------------
def user_list(request):
    all_users = User.objects.all().select_related("profile")
    customers = Customer.objects.exclude(customer_id="000")

    position_map = {
        "admin": "แอดมิน",
        "employee": "พนักงาน",
        "owner": "เจ้าของกิจการ",
    }

    users = []
    for user in all_users:
        profile = getattr(user, "profile", None)
        if profile and profile.user_code:
            user_id = profile.user_code
        else:
            continue   # 🔥 ข้าม user นี้ไปเลย

        # ✅ ใช้ first_name + last_name แทน username
        full_name = f"{user.first_name} {user.last_name}".strip()
        if not full_name.strip():  # ถ้าไม่กรอก → fallback เป็น username
            full_name = "-"

        position = (
            position_map.get(profile.position, "—") if profile else "—"
        )

        users.append(
            {
                "user_id": user_id,
                "name": full_name,  # ✅ แสดงเป็นชื่อ-สกุล
                "position": position,
                "edit_url": f"/users/{user_id}/edit/",
                "delete_url": f"/users/{user_id}/delete/",
            }
        )

    return render(
        request,
        "myapp/user_list.html",
        {"users": users, "customers": customers},
    )

def add_user(request):
    # ✅ ตรวจสอบชื่อซ้ำผ่าน AJAX
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        username = request.GET.get("username", "").strip()
        exists = User.objects.filter(username=username).exists()
        return JsonResponse({"exists": exists})

    if request.method == "POST":
        user_form = UserForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            username = user_form.cleaned_data.get("username")

            # ✅ ตรวจสอบชื่อซ้ำอีกชั้น (กันหลุด)
            if User.objects.filter(username=username).exists():
                messages.error(request, f"ชื่อผู้ใช้ '{username}' ถูกใช้แล้ว ❌")
                return redirect("myapp:add_user")

            user = user_form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            messages.success(request, f"เพิ่มผู้ใช้ {username} สำเร็จแล้ว ✅")
            return redirect("myapp:user_list")

    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    last_user = User.objects.order_by("id").last()
    next_id = last_user.id + 1 if last_user else 1
    next_user_id = f"USR-{next_id:03d}"

    return render(
        request,
        "myapp/add_user.html",
        {"user_form": user_form, "profile_form": profile_form, "next_user_id": next_user_id},
    )


def edit_user(request, user_code):
    # ✅ ใช้ user_code ตรง ๆ
    profile = get_object_or_404(UserProfile, user_code=user_code)
    user_obj = profile.user

    # ✅ Ajax check
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        username = request.GET.get("username", "").strip()
        exists = User.objects.filter(username=username).exclude(id=user_obj.id).exists()
        return JsonResponse({"exists": exists})

    if request.method == "POST":
        username = request.POST.get("username").strip()
        password = request.POST.get("password")

        if User.objects.filter(username=username).exclude(id=user_obj.id).exists():
            messages.error(request, f"ชื่อผู้ใช้ '{username}' ถูกใช้แล้ว ❌")
            return redirect("myapp:edit_user", user_code=user_code)

        user_obj.username = username
        if password:
            user_obj.set_password(password)
        user_obj.save()

        profile.address = request.POST.get("address")
        profile.phone = request.POST.get("phone")
        profile.position = request.POST.get("position")
        profile.save()

        messages.success(request, f"แก้ไขข้อมูลผู้ใช้สำเร็จ ✅")
        return redirect("myapp:user_list")

    position_choices = UserProfile._meta.get_field("position").choices

    return render(
        request,
        "myapp/edit_user.html",
        {
            "user_obj": user_obj,
            "profile": profile,
            "user_code": profile.user_code,  # ✅ แก้ตรงนี้ด้วย
            "position_choices": position_choices,
        },
    )


def delete_user(request, user_code):
    if user_code.startswith("USR-"):
        try:
            real_id = int(user_code.split("-")[1])
        except ValueError:
            return HttpResponse("Invalid user code", status=400)
    else:
        real_id = user_code

    user = get_object_or_404(User, id=real_id)
    name = user.get_full_name() or user.username
    user.delete()
    messages.success(request, f"ลบผู้ใช้ {name} เรียบร้อยแล้ว ✅")
    return redirect("myapp:user_list")


def create_user_and_profile(request):
    if request.method == "POST":
        user = User.objects.create(
            name=request.POST["name"],
            position=request.POST["position"],
            phone=request.POST["phone"],
            address=request.POST["address"],
        )

        if user.position == "employee":
            Employee.objects.create(user=user)
        elif user.position == "customer":
            Customer.objects.create(user=user)


# Product
def product_list(request):
    products = Product.objects.all()
    return render(request, "myapp/product_list.html", {"products": products})


def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        product_id = request.POST.get("product_id")

        # ✅ ตรวจสอบรหัสสินค้าซ้ำ
        if Product.objects.filter(product_id=product_id).exists():
            messages.error(request, f"รหัสสินค้า '{product_id}' มีอยู่ในระบบแล้ว ❌")
            return render(request, "myapp/add_product.html", {"form": form})

        if form.is_valid():
            form.save()
            messages.success(request, "เพิ่มสินค้าเรียบร้อยแล้ว ✅")
            return redirect("myapp:product_list")

    else:
        form = ProductForm()

    return render(request, "myapp/add_product.html", {"form": form})


def edit_product(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    old_image = product.image

    if request.method == "POST":
        product.product_name = request.POST.get("product_name")
        product.price = request.POST.get("price")
        product.weight = request.POST.get("weight")

        if request.FILES.get("image"):
            product.image = request.FILES["image"]
        else:
            product.image = old_image

        product.save()
        messages.success(request, f"แก้ไขสินค้า {product.product_name} เรียบร้อยแล้ว ✅")
        return redirect("myapp:product_list")

    return render(request, "myapp/edit_product.html", {"product": product})


def delete_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.delete()
    messages.success(request, f"ลบสินค้า {product.product_name} เรียบร้อยแล้ว ✅")
    return redirect("myapp:product_list")


# Customer
def customer_list(request):
    # ลูกค้าทั่วไป (ยกเว้น 000 system ที่ซ่อน)
    customers_regular = Customer.visible.filter(is_special=False).exclude(
        customer_id="000"
    )
    # ลูกค้าพิเศษ
    customers_special = Customer.visible.filter(is_special=True).exclude(
        customer_id="000"
    )

    return render(
        request,
        "myapp/customer_list.html",
        {
            "customers_regular": customers_regular,
            "customers_special": customers_special,
        },
    )


def add_customer(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)

            # ✅ ลูกค้าทั่วไป (is_special=False) -> generate id ถ้าไม่กรอก
            if not customer.is_special and not customer.customer_id:
                last_customer = (
                    Customer.objects.filter(is_special=False, is_hidden=False)
                    .order_by("customer_id")
                    .last()
                )
                next_id = 1
                if last_customer:
                    try:
                        next_id = int(last_customer.customer_id.split("-")[1]) + 1
                    except:
                        pass
                customer.customer_id = f"CUS-{next_id:04d}"

            # ✅ hash password ก่อนบันทึก
            raw_pw = form.cleaned_data.get("password")
            if raw_pw:
                customer.set_password(raw_pw)

            customer.save()
            return redirect("myapp:customer_list")
    else:
        # ✅ generate รหัสอัตโนมัติล่วงหน้า (เฉพาะลูกค้าทั่วไป)
        last_customer = (
            Customer.objects.filter(is_special=False, is_hidden=False)
            .order_by("customer_id")
            .last()
        )
        next_id = 1
        if last_customer:
            try:
                next_id = int(last_customer.customer_id.split("-")[1]) + 1
            except:
                pass
        auto_id = f"CUS-{next_id:04d}"
        form = CustomerForm(initial={"customer_id": auto_id})

    return render(request, "myapp/add_customer.html", {"form": form})


def edit_customer(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)

    # ✅ กันไม่ให้แก้ 000 system
    if customer.is_hidden or customer.customer_id == "000":
        messages.error(request, "ไม่อนุญาตให้แก้ไขลูกค้าทั่วไป (ค่าเริ่มต้นระบบ)")
        return redirect("myapp:customer_list")

    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save(commit=False)

            # ✅ ถ้า user กรอกรหัสใหม่ -> hash และอัพเดต
            raw_pw = form.cleaned_data.get("password")
            if raw_pw:
                customer.set_password(raw_pw)

            customer.save()
            return redirect("myapp:customer_list")
    else:
        form = CustomerForm(instance=customer)

    return render(
        request, "myapp/edit_customer.html", {"form": form, "customer": customer}
    )


def delete_customer(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)

    if customer.is_hidden or customer.customer_id == "000":
        messages.error(request, "ไม่สามารถลบลูกค้าทั่วไป (ค่าเริ่มต้นระบบ) ได้")
        return redirect("myapp:customer_list")

    customer.delete()
    messages.success(request, "ลบลูกค้าเรียบร้อย")
    return redirect("myapp:customer_list")


# Employee
def employee_list(request):
    employees = Employee.objects.select_related("user").all()
    return render(request, "myapp/employee_list.html", {"employees": employees})


# Add employee
def add_employee(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save(commit=False)

            # ✅ สร้าง User ที่ผูกกับ Employee
            last_user = User.objects.order_by("id").last()
            next_id = last_user.id + 1 if last_user else 1
            username = f"EMP-{next_id:03d}"

            user = User.objects.create(
                username=username,
                first_name=request.POST.get("first_name", ""),  # ถ้าอยากเพิ่มชื่อจริง
                last_name=request.POST.get("last_name", ""),
                password=make_password("default123"),  # ✅ set default password
            )

            employee.user = user
            employee.save()
            return redirect("myapp:employee_list")
    else:
        form = EmployeeForm()

    return render(request, "myapp/add_employee.html", {"form": form})


# Edit employee
def edit_employee(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    form = EmployeeForm(request.POST or None, instance=employee)
    if form.is_valid():
        form.save()
        return redirect("myapp:employee_list")
    return render(
        request,
        "myapp/add_employee.html",
        {"form": form, "edit": True, "employee": employee},
    )

def sale_page(request):

    products = Product.objects.all()
    customers = Customer.objects.all()
    sales = Sale.objects.all().order_by("-id")[:20]

    preview_code = "S" + timezone.now().strftime("%Y%m%d%H%M%S")

    shipping_rates = [
        {"weight":5,"rate":20},
        {"weight":10,"rate":40},
        {"weight":20,"rate":60},
        {"weight":50,"rate":100},
    ]

    return render(request,"sale.html",{
        "products":products,
        "customers":customers,
        "sales":sales,
        "preview_code":preview_code,
        "shipping_rates":shipping_rates
    })


def add_sale(request):
    if request.method == "POST":

        sale_code = request.POST.get("sale_code")
        sale_date = parse_date(request.POST.get("sale_date"))
        customer_id = request.POST.get("customer_id")
        shipping_cost = float(request.POST.get("shipping_cost", 0))

        customer = get_object_or_404(Customer, customer_id=customer_id)

        sale = Sale.objects.create(
            sale_code=sale_code,
            sale_date=sale_date,
            customer=customer,
            shipping_fee=shipping_cost,
            created_by=request.user
        )

        items_json = request.POST.get("items_json")
        print("📌 items_json:", items_json)
        if not items_json:
            messages.error(request, "ไม่มีสินค้า")
            return redirect("sale_page")

        items = json.loads(items_json)
        print("📌 items parsed:", items)
        for item in items:
            product = get_object_or_404(Product, product_id=item["product_id"])

            SaleItem.objects.create(
                sale=sale,
                product=product,
                price=item["price"],
                quantity=item["qty"]
            )

        messages.success(request, "บันทึกสำเร็จ")
        return redirect("sale_receipt", sale_id=sale.id)

    return redirect("sale_page")

def sale_receipt(request, sale_id):

    sale = get_object_or_404(Sale, id=sale_id)

    return render(request,"receipt.html",{
        "sale":sale
    })
# Delete employee
def delete_employee(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    employee.user.delete()  # ✅ ลบ user ด้วย (เพราะ OneToOne)
    return redirect("myapp:employee_list")


# Sale
# ====== หน้าเดียว (ฟอร์ม + รายงาน) ======
def sale_list(request):
    products = Product.objects.all().order_by("product_id")
    customers = Customer.visible.all().order_by("name")

    # ค่าเริ่มต้นไม่แสดงอะไร
    sales = Sale.objects.none()

    # ✅ ถ้ามี query date -> filter
    filter_date = request.GET.get("filter_date")
    if filter_date:
        sales = Sale.objects.filter(sale_date=parse_date(filter_date)).order_by("-id")

    # -------- generate preview_code เดิมคงไว้ --------
    today_str = timezone.now().strftime("%Y%m")
    prefix = f"SA-{today_str}"
    last_sale = (
        Sale.objects.filter(sale_code__startswith=prefix).order_by("-id").first()
    )

    if last_sale and last_sale.sale_code:
        try:
            last_number = int(last_sale.sale_code.split("-")[-1])
        except ValueError:
            last_number = 0
        next_number = last_number + 1
    else:
        next_number = 1

    preview_code = f"{prefix}-{next_number:03d}"

    return render(
        request,
        "myapp/sale_list.html",
        {
            "products": products,
            "customers": customers,
            "sales": sales,
            "preview_code": preview_code,
            "shipping_rates": json.dumps(
                list(
                    ShippingRate.objects.all()
                    .order_by("weight")
                    .values("weight", "rate")
                ),
                cls=DjangoJSONEncoder,
            ),
        },
    )

def dashboard(request):

    total_sales = Sale.objects.count()
    total_products = Product.objects.count()
    total_customers = Customer.objects.count()
    total_delivery = Delivery.objects.count()
    total_payment = Payment.objects.count()

    revenue = Payment.objects.aggregate(total=Sum('pay_total'))['total'] or 0

    pending = Sale.objects.filter(status=1).count()
    waiting = Sale.objects.filter(status=2).count()
    shipping = Sale.objects.filter(status=3).count()
    success = Sale.objects.filter(status=4).count()

    # 🔥 Top Products
    top_products = SaleItem.objects.values(
        'product__product_name'
    ).annotate(
        total=Sum('quantity')
    ).order_by('-total')[:5]

    # 🔥 Recent Orders
    recent_sales = Sale.objects.select_related('customer').order_by('-id')[:5]

    # 🔥 Customers / Delivery / Payment
    customers = Customer.objects.all().order_by('-id')
    deliveries = Delivery.objects.select_related('sale__customer').order_by('-delivery_id')
    payments = Payment.objects.select_related('sale__customer').order_by('-sale_id')

    # =====================
    # ✅ D8 รายงานสินค้า
    # =====================
    report_products = SaleItem.objects.values(
        'product__product_name'
    ).annotate(
        total_qty=Sum('quantity')
    ).order_by('-total_qty')

    # =====================
    # ✅ D9 รายงานการขาย
    # =====================
    report_sales = Sale.objects.values(
        'status'
    ).annotate(
        total=Count('id')
    )

    # =====================
# ✅ D10 รายงานการเงิน
# =====================
    report_finance = Payment.objects.aggregate(
    total_income=Sum('pay_total'),
    total_transactions=Count('*'),
    )

    chart_labels = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    chart_data = [5,10,7,12,8,15,9]
    context = {
    
        'total_sales': total_sales,
        'total_products': total_products,
        'total_customers': total_customers,
        'total_delivery': total_delivery,
        'total_payment': total_payment,
        'revenue': revenue,

        'pending': pending,
        'waiting': waiting,
        'shipping': shipping,
        'success': success,

        'top_products': top_products,
        'recent_sales': recent_sales,

        'customers': customers,
        'deliveries': deliveries,
        'payments': payments,

        # 🔥 REPORT
        'report_products': report_products,
        'report_sales': report_sales,
        'report_finance': report_finance,

        'chart_labels': chart_labels,
        'chart_data': chart_data,
    }
    return render(request,'myapp/dashboard.html',context)


@transaction.atomic
def add_sale(request):
    if request.method == "POST":
        print("📌 RAW POST:", request.POST.dict())

        customer_code = request.POST.get("customer_id")
        sale_date = parse_date(request.POST.get("sale_date"))
        note = request.POST.get("note", "")
        items_json = request.POST.get("items_json", "[]")

        # ✅ กัน sale_date เป็น None (สำคัญมาก)
        if not sale_date:
            sale_date = timezone.now().date()

        # ✅ parse cart
        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            items = []

        if not items:
            messages.error(request, "ไม่มีสินค้าในรายการขาย")
            return redirect("myapp:sale_list")

        # ✅ หาลูกค้า
        customer = Customer.visible.filter(customer_id=customer_code).first()
        if not customer:
            messages.error(request, f"ไม่พบลูกค้า {customer_code}")
            return redirect("myapp:sale_list")

        # -------- generate sale_code --------
        today_str = timezone.now().strftime("%Y%m")
        prefix = f"SA-{today_str}"
        last_sale = Sale.objects.filter(
            sale_code__startswith=prefix
        ).order_by("-id").first()

        if last_sale and last_sale.sale_code:
            try:
                last_number = int(last_sale.sale_code.split("-")[-1])
            except ValueError:
                last_number = 0
            next_number = last_number + 1
        else:
            next_number = 1

        sale_code = f"{prefix}-{next_number:03d}"

        # ✅ สร้าง Sale
        sale = Sale.objects.create(
            sale_code=sale_code,
            customer=customer,
            sale_date=sale_date,
            note=note,
            status=4,
        )

        # ✅ เพิ่มสินค้า + (ตัวเลือก: ตัด stock)
        for it in items:
            pid = it.get("product_id") or it.get("productId")
            price = it.get("price") or it.get("price_per_unit") or 0
            qty = it.get("qty") or it.get("quantity") or 1

            if not pid:
                continue

            product = Product.objects.filter(product_id=pid).first()
            if not product:
                continue

            SaleItem.objects.create(
                sale=sale,
                product=product,
                price=price,
                quantity=qty,
            )

            # 🔥 (แนะนำ) ตัด stock
            # product.stock -= int(qty)
            # product.save()

        # ✅ คำนวณค่าขนส่ง
        sale.shipping_fee = sale.calculate_shipping()
        sale.save()

        messages.success(request, f"บันทึกการขาย {sale.sale_code} เรียบร้อย")

        # ❗ แก้ redirect ให้ตรง urls.py
        return redirect("myapp:sale_receipt", sale_id=sale.id)

    return redirect("myapp:sale_list")


def edit_sale(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == "POST":
        sale.sale_date = parse_date(request.POST.get("sale_date")) or sale.sale_date
        # ✅ แก้ให้ update ผ่าน object
        customer_id = request.POST.get("customer_id")
        if customer_id:
            sale.customer = get_object_or_404(Customer.visible, pk=customer_id)

        sale.employee_id = request.POST.get("employee_id") or sale.employee_id
        sale.shipping_fee = float(request.POST.get("shipping_fee") or sale.shipping_fee)
        sale.note = request.POST.get("note") or ""
        sale.status = int(request.POST.get("status") or sale.status)
        sale.save()
        messages.success(request, "แก้ไขข้อมูลการขายเรียบร้อย")
        return redirect("myapp:sale_list")
    return render(request, "myapp/edit_sale.html", {"sale": sale})


def delete_sale(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == "POST":
        sale.delete()
        messages.success(request, "ลบการขายเรียบร้อย")
        return redirect("myapp:sale_list")
    return render(request, "myapp/delete_sale.html", {"sale": sale})


# ===============================
# ProductReceive: หน้าเดียว รวมฟอร์ม + รายงาน
# ===============================
# ✅ STEP 1: ฟอร์

def product_receive_list(request):
    # โหลดสินค้า
    products = Product.objects.all().order_by("product_id")

    # ยังไม่โหลดประวัติ ถ้ายังไม่เลือกวันที่
    product_receives = ProductReceive.objects.none()

    filter_date = request.GET.get("filter_date")
    if filter_date:
        product_receives = (
            ProductReceive.objects.filter(receive_date=filter_date)
            .prefetch_related("items__product")
            .order_by("-receive_id")
        )

    # Auto generate รหัสรับสินค้า
    today = datetime.today().strftime("%Y%m")
    prefix = f"RCV-{today}"
    last = ProductReceive.objects.filter(receive_id__startswith=prefix).order_by("-receive_id").first()
    last_number = int(last.receive_id.split("-")[-1]) + 1 if last else 1
    auto_id = f"{prefix}-{last_number:04d}"

    return render(
        request,
        "myapp/product_receive_list.html",
        {
            "products": products,
            "product_receives": product_receives,
            "auto_id": auto_id,
            "filter_date": filter_date or "",
        },
    )

def confirm_receive(request):
    if request.method == "POST":
        # logic บันทึกข้อมูลจริงลง DB
        return redirect("myapp:product_receive_list")
    return redirect("myapp:product_receive_list")



# ✅ STEP 2: Preview


def product_receive_preview(request):
    if request.method == "POST":
        receive_date = request.POST.get("receive_date")
        items_json = request.POST.get("items_json")
        items = json.loads(items_json)

        # ✅ ไม่ส่ง receive_id ให้ model generate เอง
        receive = ProductReceive.objects.create(
            receive_date=receive_date, user=request.user
        )

        # ✅ รายการสินค้า
        for it in items:
            product = Product.objects.get(product_id=it["productId"])
            ProductReceiveItem.objects.create(
                receive=receive, product=product, quantity=it["qty"]
            )

        return redirect("myapp:product_receive_list")

    return redirect("myapp:product_receive_list")


# ✅ STEP 3: บันทึกจริง
@transaction.atomic
def add_product_receive(request):
    if request.method != "POST":
        return redirect("myapp:product_receive_list")

    receive_date = (
        parse_date(request.POST.get("receive_date") or "") or timezone.now().date()
    )

    try:
        items = json.loads(request.POST.get("items_json") or "[]")
    except json.JSONDecodeError:
        items = []

    if not items:
        messages.error(request, "ไม่มีสินค้าในรายการ")
        return redirect("myapp:product_receive_list")

    # ✅ ให้ model generate receive_id เอง
    pr = ProductReceive.objects.create(
        receive_date=receive_date,
        user=request.user,
    )

    # save details
    for it in items:
        pid = (it.get("product_id") or "").strip()
        qty = int(it.get("qty") or 0)
        if not pid or qty <= 0:
            transaction.set_rollback(True)
            messages.error(request, "พบข้อมูลสินค้าไม่ถูกต้อง")
            return redirect("myapp:product_receive_list")

        product = get_object_or_404(Product, product_id=pid)
        ProductReceiveItem.objects.create(receive=pr, product=product, quantity=qty)

    messages.success(request, f"บันทึกการรับ {pr.receive_id} เรียบร้อย")
    return redirect("myapp:product_receive_history")


# ✅ STEP 4: History
def product_receive_history(request):
    filter_date = request.GET.get("filter_date")

    product_receives = ProductReceive.objects.none()
    if filter_date:
        product_receives = (
            ProductReceive.objects.filter(receive_date=filter_date)
            .select_related("user")
            .prefetch_related("items__product")
            .order_by("-receive_date", "-receive_id")
        )

    return render(
        request,
        "myapp/product_receive_history.html",  # ← สำหรับค้นหาประวัติ
        {
            "product_receives": product_receives,
            "filter_date": filter_date,
        },
    )

# Payment
def payment_list(request):
    payments = Payment.objects.all()
    return render(request, "myapp/payment_list.html", {"payments": payments})


def add_payment(request):
    sale_id = request.GET.get("sale_id")
    initial = {}
    if sale_id:
        try:
            initial["sale"] = Sale.objects.get(pk=sale_id)
        except Sale.DoesNotExist:
            pass

    if request.method == "POST":
        form = PaymentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("myapp:payment_list")
    else:
        form = PaymentForm(initial=initial)

    return render(request, "myapp/add_payment.html", {"form": form})


def edit_payment(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id)
    form = PaymentForm(request.POST or None, request.FILES or None, instance=payment)
    if form.is_valid():
        form.save()
        return redirect("myapp:payment_list")
    return render(
        request,
        "myapp/add_payment.html",
        {"form": form, "edit": True, "payment": payment},
    )


def delete_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == "POST":
        payment.delete()
        return redirect("myapp:payment_list")
    return render(request, "myapp/delete_payment.html", {"payment": payment})


# PaymentConfirmation
def payment_confirmation_list(request):
    confirmations = PaymentConfirmation.objects.all()
    return render(
        request,
        "myapp/payment_confirmation_list.html",
        {"confirmations": confirmations},
    )


def add_payment_confirmation(request):
    if request.method == "POST":
        form = PaymentConfirmationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("myapp:payment_confirmation_list")
    else:
        form = PaymentConfirmationForm()
    return render(request, "myapp/add_payment_confirmation.html", {"form": form})


def edit_payment_confirmation(request, confirmation_id):
    confirmation = get_object_or_404(PaymentConfirmation, pk=confirmation_id)
    form = PaymentConfirmationForm(request.POST or None, instance=confirmation)
    if form.is_valid():
        form.save()
        return redirect("myapp:payment_confirmation_list")
    return render(
        request,
        "myapp/add_payment_confirmation.html",  # ใส่ underscore _
        {"form": form, "edit": True, "confirmation": confirmation},
    )


def delete_payment_confirmation(request, confirmation_id):
    confirmation = get_object_or_404(PaymentConfirmation, pk=confirmation_id)
    if request.method == "POST":
        confirmation.delete()
        return redirect("myapp:payment_confirmation_list")
    return render(
        request,
        "myapp/delete_payment_confirmation.html",
        {"confirmation": confirmation},
    )


# Delivery
def delivery_list(request):
    deliveries = Delivery.objects.select_related('sale', 'user').all()
    sales = Sale.objects.select_related("customer").all()

    return render(request, "myapp/delivery_list.html", {
        "deliveries": deliveries,
        "sales": sales,
    })

def add_delivery(request):
    if request.method == "POST":
        form = DeliveryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("myapp:delivery_list")  # <-- แก้ตรงนี้
    else:
        form = DeliveryForm()
    return render(request, "myapp/add_delivery.html", {"form": form})


def edit_delivery(request, delivery_id):
    delivery = get_object_or_404(Delivery, pk=delivery_id)
    form = DeliveryForm(request.POST or None, instance=delivery)
    if form.is_valid():
        form.save()
        return redirect("myapp:delivery_list")
    return render(
        request,
        "myapp/add_delivery.html",
        {"form": form, "edit": True, "delivery": delivery},
    )


def delete_delivery(request, delivery_id):
    delivery = get_object_or_404(Delivery, pk=delivery_id)
    delivery.delete()
    return redirect("myapp:delivery_list")


def confirm_sale(request, sale_id):
    sale = get_object_or_404(Sale, pk=sale_id)
    if sale.status == 0:  # รอการยืนยัน
        sale.status = 1  # รอการแจ้งชำระเงิน
        sale.save()
        messages.success(request, f"ยืนยันการขาย {sale.sale_id} เรียบร้อยแล้ว")
    else:
        messages.warning(request, "สถานะการขายนี้ไม่สามารถยืนยันได้")
    # สมมติ redirect กลับหน้ารายการขาย
    return redirect("myapp:sale_list")


# ข้อมูลร้านค้า
def store_list(request):
    # ถ้ามีร้านค้าอยู่แล้ว → redirect ไปแก้ไข
    store = Store.objects.first()
    if store:
        return redirect("myapp:store_edit", pk=store.pk)
    else:
        # ถ้ายังไม่มี → redirect ไปสร้างใหม่
        return redirect("myapp:store_create")


def store_edit(request, pk):
    store = get_object_or_404(Store, pk=pk)
    if request.method == "POST":
        form = StoreForm(request.POST, instance=store)
        if form.is_valid():
            form.save()
            messages.success(request, "บันทึกข้อมูลร้านเรียบร้อยแล้ว ✅")
            return redirect("myapp:store_edit", pk=store.pk)
        else:
            messages.error(request, "ไม่สามารถบันทึกข้อมูลได้ ❌ โปรดตรวจสอบอีกครั้ง")
    else:
        form = StoreForm(instance=store)

    return render(request, "myapp/store_form.html", {"form": form, "store": store})


def store_create(request):
    if request.method == "POST":
        form = StoreForm(request.POST)
        if form.is_valid():
            store = form.save()
            return redirect("myapp:store_edit", pk=store.pk)
    else:
        form = StoreForm()
    return render(request, "myapp/store_form.html", {"form": form})


def store_delete(request, pk):
    store = get_object_or_404(Store, pk=pk)
    if request.method == "POST":
        store.delete()
        return redirect("myapp:store_list")
    return render(request, "myapp/store_confirm_delete.html", {"store": store})


# ข้อมูลอัตราค่าขนส่ง
def shipping_rate_list(request):
    rates = ShippingRate.objects.all()
    return render(request, "myapp/shipping_rate_list.html", {"rates": rates})


def shipping_rate_create(request):
    if request.method == "POST":
        form = ShippingRateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "เพิ่มอัตราค่าขนส่งเรียบร้อยแล้ว ✅")
            return redirect("myapp:shipping_rate_list")
        else:
            for error in form.errors.get("__all__", []):
                messages.error(request, error)
    else:
        form = ShippingRateForm()
    return render(request, "myapp/shipping_rate_form.html", {"form": form})


def shipping_rate_edit(request, pk):
    rate = get_object_or_404(ShippingRate, pk=pk)
    if request.method == "POST":
        form = ShippingRateForm(request.POST, instance=rate)
        if form.is_valid():
            form.save()
            messages.success(request, "แก้ไขอัตราค่าขนส่งเรียบร้อยแล้ว ✅")
            return redirect("myapp:shipping_rate_list")
        else:
            for error in form.errors.get("__all__", []):
                messages.error(request, error)
    else:
        form = ShippingRateForm(instance=rate)
    return render(request, "myapp/shipping_rate_form.html", {"form": form})
def checkout_payment(request, sale_id):

    sale = Sale.objects.get(id=sale_id)

    if request.method == "POST":

        slip = request.FILES.get("slip_image")

        Payment.objects.create(
            sale=sale,
            pay_total=sale.get_total(),
            pay_type=0,
            slip_image=slip
        )

        sale.status = 1
        sale.save()

        return redirect("payment_success")

    return render(request,"checkout.html",{
        "sale":sale
    })

def shipping_rate_delete(request, pk):
    rate = get_object_or_404(ShippingRate, pk=pk)
    rate.delete()
    messages.success(request, "ลบอัตราค่าขนส่งเรียบร้อยแล้ว ✅")
    return redirect("myapp:shipping_rate_list")

def checkout_view(request):

    # ----------------------------
    # cart key
    # ----------------------------
    if request.user.is_authenticated:
        cart_key = f"cart_user_{request.user.id}"
    elif request.session.get("customer_id"):
        cart_key = f"cart_customer_{request.session.get('customer_id')}"
    else:
        cart_key = "cart_guest"

    cart = request.session.get(cart_key, {})

    if not cart:
        return redirect("myapp:cart")

    # ----------------------------
    # cart items
    # ----------------------------
    items = []
    total = 0
    total_weight = 0

    for product_id, qty in cart.items():
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            continue

        subtotal = product.price * qty
        weight = (product.weight or 0) * qty

        total += subtotal
        total_weight += weight

        items.append({
            "product": product,
            "qty": qty,
            "subtotal": subtotal,
            "weight": product.weight,
        })

    # ----------------------------
    # shipping
    # ----------------------------
    shipping_fee = 25 if total_weight <= 1 else 350
    grand_total = total + shipping_fee

    # ----------------------------
    # customer auto fill
    # ----------------------------
    customer = None
    full_name = ""
    phone = ""
    address = ""

    # ลูกค้าปกติ
    customer_id = request.session.get("customer_id")
    if customer_id:
        customer = Customer.objects.filter(customer_id=customer_id).first()

    if customer:
        full_name = customer.name
        phone = customer.phone
        address = customer.address

    # Admin / Employee
    elif request.user.is_authenticated:
        full_name = request.user.get_full_name()

        if hasattr(request.user, "profile"):
            phone = request.user.profile.phone
            address = request.user.profile.address

    # ----------------------------
    # submit payment
    # ----------------------------
    if request.method == "POST":

        name = request.POST.get("name")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        slip = request.FILES.get("slip_image")

        if not customer:
            customer = Customer.objects.filter(customer_id="000").first()

        sale = Sale.objects.create(
            customer=customer,
            shipping_fee=shipping_fee,
            status=2,
            note=f"{name} | {phone} | {address}"
        )

        for item in items:
            SaleItem.objects.create(
                sale=sale,
                product=item["product"],
                price=item["product"].price,
                quantity=item["qty"]
            )

        Payment.objects.create(
            sale=sale,
            pay_total=grand_total,
            pay_type=0,
            slip_image=slip
        )

        # clear cart
        request.session[cart_key] = {}
        request.session.modified = True

        return redirect("myapp:customer_orders")

    # ----------------------------
    # render page
    # ----------------------------
    return render(request, "checkout.html", {
        "items": items,
        "total": total,
        "shipping_fee": shipping_fee,
        "grand_total": grand_total,

        # auto fill data
        "full_name": full_name,
        "phone": phone,
        "address": address,
    })
def customer_orders(request):

    customer = None

    # ลูกค้าปกติ
    customer_id = request.session.get("customer_id")
    if customer_id:
        customer = Customer.objects.filter(customer_id=customer_id).first()

    # admin / employee
    if not customer and request.user.is_authenticated:
        customer = Customer.objects.filter(customer_id="000").first()

    if not customer:
        return redirect("myapp:login")

    orders = Sale.objects.filter(customer=customer)\
        .prefetch_related("items__product")\
        .order_by("-sale_date")

    return render(request, "orders.html", {
        "orders": orders
    })
from django.shortcuts import render, get_object_or_404
from .models import Sale

def invoice_view(request, sale_id):
    sale = get_object_or_404(
        Sale.objects.select_related("customer")
        .prefetch_related("items__product", "payment"),
        pk=sale_id
    )
    return render(request, "invoice.html", {
        "sale": sale
    })
def report_sales(request):
    sales = Sale.objects.select_related("customer").all().order_by("-id")

    return render(request, "myapp/report_sales.html", {
        "sales": sales
    })
  
def sale_preview(request):
    if request.method == "POST":
        import json

        # ✅ ต้องมีบรรทัดนี้ก่อน
        raw_json = request.POST.get("items_json", "[]")

        try:
            cart = json.loads(raw_json)
        except:
            cart = []

        items = []
        subtotal = 0

        for item in cart:
            total = item["price"] * item["qty"]
            subtotal += total

            items.append({
                "name": item["name"],
                "qty": item["qty"],
                "total": total
            })

        shipping = float(request.POST.get("shipping_cost", 0))
        grand_total = subtotal + shipping

        return render(request, "myapp/sale_preview.html", {
            "items": items,
            "subtotal": subtotal,
            "shipping": shipping,
            "grand_total": grand_total,

            # ✅ ตอนนี้ใช้ได้แล้ว
            "cart_json": raw_json,
        })
def pay_api(request, id):
            sale = get_object_or_404(Sale, id=id)

            try:
                payment = Payment.objects.get(sale=sale)
            except Payment.DoesNotExist:
                 return JsonResponse({'error': 'no payment'}, status=404)

            return JsonResponse({
                'id': sale.id,
                'cus': sale.customer.name,
                'date': sale.sale_date.strftime('%d/%m/%Y'),
                'slip': payment.slip_image.url if payment.slip_image else ''
            })
def pay_list(request):
    sales = Sale.objects.filter(status=2)
    print("DEBUG:", sales)
    return render(request, 'pay/pay.html', {'sales': sales})
@login_required
def pay_ok(request, id):
    if request.method != 'POST':
        return JsonResponse({'error': 'invalid'}, status=400)

    sale = get_object_or_404(Sale, id=id)

    # 🔒 กันกดซ้ำ
    if sale.status != 2:
        return JsonResponse({'error': 'already processed'}, status=400)

    try:
        payment = Payment.objects.get(sale=sale)
    except Payment.DoesNotExist:
        return JsonResponse({'error': 'no payment'}, status=400)

    # 🔥 ทำทุกอย่างใน transaction เดียว
    with transaction.atomic():

        # 1️⃣ เปลี่ยนสถานะ
        sale.status = 3  # รอจัดส่ง
        sale.save()

        # 2️⃣ ตัด stock
        for item in sale.items.all():
            Product.objects.filter(
                pk=item.product.pk,
                quantity__gte=item.quantity
            ).update(quantity=F('quantity') - item.quantity)

        # 3️⃣ สร้างใบยืนยัน (ถ้ายังไม่มี)
        if not PaymentConfirmation.objects.filter(payment=payment).exists():
            PaymentConfirmation.objects.create(
                payment=payment,
                user=request.user
            )

    return JsonResponse({'ok': True})
def confirm_order_view(request):
    if request.user.is_authenticated:
        cart_key = f"cart_user_{request.user.id}"
    elif request.session.get("customer_id"):
        cart_key = f"cart_customer_{request.session.get('customer_id')}"
    else:
        cart_key = "cart_guest"

    cart = request.session.get(cart_key, {})

    if not cart:
        return redirect("myapp:cart")

    items = []
    total = 0
    total_weight = 0
    total_items = 0

    for product_id, qty in cart.items():
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            continue

        subtotal = product.price * qty
        weight = (product.weight or 0) * qty

        total += subtotal
        total_weight += weight
        total_items += qty

        items.append({
            "product": product,
            "qty": qty,
            "subtotal": subtotal,
            "weight": weight,
        })

    shipping_fee = 0
    rates = ShippingRate.objects.all().order_by("weight")

    for r in rates:
        if total_weight <= r.weight:
            shipping_fee = r.rate
            break

    if shipping_fee == 0 and rates.exists():
        shipping_fee = rates.last().rate

    grand_total = total + shipping_fee

    name = ""
    phone = ""
    address = ""

    customer = None
    if request.session.get("customer_id"):
        customer = Customer.objects.filter(
            customer_id=request.session.get("customer_id")
        ).first()

    if customer:
        name = customer.name
        phone = customer.phone
        address = customer.address

    return render(request, "confirm_order.html", {
        "items": items,
        "total": total,
        "shipping_fee": shipping_fee,
        "grand_total": grand_total,
        "total_items": total_items,
        "name": name,
        "phone": phone,
        "address": address,
    })
def receipt(request, pk):
    sale = Sale.objects.get(pk=pk)
    return render(request, "myapp/receipt.html", {"sale": sale})   