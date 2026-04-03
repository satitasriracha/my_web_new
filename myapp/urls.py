from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = "myapp"

urlpatterns = [

    # ====== Home ======
    path("", views.home, name="root_home"),
  
    path("home/", views.home, name="home"),
# path('add_to_cart/<str:product_id>/', views.add_to_cart, name='add_to_cart'),
path("login/", views.login_view, name="login"),
    # ====== Shop ======
    path("shop/products/", views.products, name="products"),

    # ====== Cart ======
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<str:pk>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<slug:pk>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/update/<slug:pk>/", views.update_cart, name="update_cart"),

    # ====== Authentication ======
    path("register/", views.register, name="register"),
    
    path("logout/", views.logout_view, name="logout"),
    path("forgot/", views.forgot_password_view, name="forgot_password"),

    path("password_reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),

    # ====== Users ======
    path("users/", views.user_list, name="user_list"),
    path("users/add/", views.add_user, name="add_user"),
    path("users/<str:user_code>/edit/", views.edit_user, name="edit_user"),
    path("users/<str:user_code>/delete/", views.delete_user, name="delete_user"),

    # ====== Products ======
    path("products/", views.product_list, name="product_list"),
    path("products/add/", views.add_product, name="add_product"),
    path("products/<str:product_id>/edit/", views.edit_product, name="edit_product"),
    path("products/<str:product_id>/delete/", views.delete_product, name="delete_product"),

    # ====== Customers ======
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/add/", views.add_customer, name="add_customer"),
    path("customers/<str:customer_id>/edit/", views.edit_customer, name="edit_customer"),
    path("customers/<str:customer_id>/delete/", views.delete_customer, name="delete_customer"),

    # ====== POS ขายหน้าร้าน ======
   path("sale/", views.sale_list, name="sale_list"),
    path("sale/save/", views.add_sale, name="add_sale"),
    path("receipt/<int:sale_id>/", views.sale_receipt, name="sale_receipt"),
# urls.py

# urls.py
path('delivery/', views.delivery_list, name='delivery_list'),
path('delivery/create/', views.delivery_create, name='delivery_create'),

# ✅ เพิ่มตัวนี้
path('delivery/tracking/', views.delivery_tracking, name='delivery_tracking'),
path('dashboard/', views.dashboard, name='dashboard'),
path('delivery/<int:delivery_id>/edit/', views.edit_delivery, name='edit_delivery'),
path('delivery/<int:delivery_id>/delete/', views.delete_delivery, name='delete_delivery'),
path('update-sale-status/<int:pk>/', views.update_sale_status, name='update_sale_status'),
    # ====== Sales History ======
    path("sales/", views.sale_list, name="sale_list"),
    path("sales/<str:sale_id>/edit/", views.edit_sale, name="edit_sale"),
    path("sales/<str:sale_id>/delete/", views.delete_sale, name="delete_sale"),

    # ====== Employees ======
    path("employees/", views.employee_list, name="employee_list"),
    path("employees/add/", views.add_employee, name="add_employee"),
    path("employees/<str:employee_id>/edit/", views.edit_employee, name="edit_employee"),
    path("employees/<str:employee_id>/delete/", views.delete_employee, name="delete_employee"),

    # ====== Product Receive ======
    path("product_receive/", views.product_receive_list, name="product_receive_list"),
    path("product_receive/preview/", views.product_receive_preview, name="product_receive_preview"),
    path("product_receive/add/", views.add_product_receive, name="add_product_receive"),
    path("receive/history/", views.product_receive_history, name="product_receive_history"),
    path("product_receive/confirm/", views.confirm_receive, name="confirm_receive"),

    # ====== Orders ======
    path("orders/", views.customer_orders, name="customer_orders"),
    path("invoice/<int:sale_id>/", views.invoice_view, name="invoice"),

    # ====== Payment ======
    path("payment/", views.payment_list, name="payment_list"),
    path("payment/add/", views.add_payment, name="add_payment"),
    path("payment/<str:payment_id>/edit/", views.edit_payment, name="edit_payment"),
    path("payment/<str:payment_id>/delete/", views.delete_payment, name="delete_payment"),

    # ====== Payment Confirmation ======
    path("payment_confirmation/", views.payment_confirmation_list, name="payment_confirmation_list"),
    path("payment_confirmation/add/", views.add_payment_confirmation, name="add_payment_confirmation"),
    path("payment_confirmation/<str:confirmation_id>/edit/", views.edit_payment_confirmation, name="edit_payment_confirmation"),
    path("payment_confirmation/<str:confirmation_id>/delete/", views.delete_payment_confirmation, name="delete_payment_confirmation"),

    # ====== Delivery ======
    path("delivery/", views.delivery_list, name="delivery_list"),
    path("delivery/add/", views.add_delivery, name="add_delivery"),
    path("delivery/<str:delivery_id>/edit/", views.edit_delivery, name="edit_delivery"),
    path("delivery/<str:delivery_id>/delete/", views.delete_delivery, name="delete_delivery"),

    # ====== Store ======
    path("stores/", views.store_list, name="store_list"),
    path("stores/create/", views.store_create, name="store_create"),
    path("stores/<str:pk>/edit/", views.store_edit, name="store_edit"),
    path("stores/<str:pk>/delete/", views.store_delete, name="store_delete"),

    # ====== Shipping Rate ======
    path("shipping/", views.shipping_rate_list, name="shipping_rate_list"),
    path("shipping/add/", views.shipping_rate_create, name="shipping_rate_create"),
    path("shipping/<int:pk>/edit/", views.shipping_rate_edit, name="shipping_rate_edit"),
    path("shipping/<int:pk>/delete/", views.shipping_rate_delete, name="shipping_rate_delete"),

    # ====== Checkout ======
    path("checkout/", views.checkout_view, name="checkout"),
    path('report/sales/', views.report_sales, name='report_sales'),
    
    

]